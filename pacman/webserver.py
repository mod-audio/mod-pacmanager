# -*- coding: utf-8 -*-

# Copyright 2012-2013 AGR Audio, Industria e Comercio LTDA. <contato@portalmod.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json, subprocess, re, glob, time
import os, sys
from tornado import web, gen, ioloop, options, template
from pacman import fileserver
from pacman.settings import check_environment

from pacman.settings import (DOWNLOAD_TMP_DIR, REPOSITORY_PUBLIC_KEY, LOCAL_REPOSITORY_DIR,
                             HTML_DIR, PORT, REPOSITORY_ADDRESS, PACMAN_COMMAND, IHM_RESET_SCRIPT)


def change_repo(repo):
    global REPOSITORY_ADDRESS
    url = "http://packages.portalmod.com/api/"
    if repo == "testing":
        url = "http://packages-testing.portalmod.com/api/"
    elif repo == "homolog":
        url = "http://packages-homologation.portalmod.com/api/"
    REPOSITORY_ADDRESS = url
    try:
        fh = open("/root/repository", "w")
        fh.write(url)
        fh.close()
    except IOError:
        # can't open/create file
        pass

def change_cloud(cloud):
    url = "http://cloud.portalmod.com/"
    if cloud == "testing":
        url = "http://cloud-testing.portalmod.com/"
    try:
        fh = open("/root/cloud", "w")
        fh.write(url)
        fh.close()
    except IOError:
        # can't open/create file
        pass

def get_systemd_status(service):
    command = ['systemctl', 'status', service]
    sp = subprocess.Popen(command, stdout=subprocess.PIPE)
    sp.wait()
    output = sp.stdout.readlines()
    status = [line for line in output if line.strip().startswith("Active")]
    status = status[0].strip().split("Active:")[1].strip()
    return status

def run_systemctl_command(command, service):
    return subprocess.call(['systemctl', command, service])

def run_pacman(action, package_name=None):
    """
    Runs pacman with given parameters.
    Write its information (pid, command, output, input) to filesystem
    and hangs this process until it's finished
    """
    remove_lock()
    command = [PACMAN_COMMAND, '--noconfirm', '--force', action]
    if package_name:
        command.append(package_name)

    cmd = open('/tmp/pacman.cmd', 'w')
    out = open('/tmp/pacman.out', 'w')
    err = open('/tmp/pacman.err', 'w')
    pid = open('/tmp/pacman.pid', 'w')
    res = open('/tmp/pacman.res', 'w')

    cmd.write(' '.join(command))
    cmd.close()

    proc = subprocess.Popen(command,
                            stdout=out,
                            stderr=err)
    pid.write('%d' % proc.pid)
    pid.close()

    proc.wait()

    out.close()
    err.close()

    result = proc.poll()

    res.write('%d' % result)
    res.close()

    return result == 0

def parse_pacman_output():
    """
    Gets a pacman -S command output and retrieves a list of packages that it would install
    """
    output = open('/tmp/pacman.out').read()
    return [ re.sub(r'.*://.*/', '', line)
             for line in output.split() if "://" in line ]

def clean_repo():
    filelist = glob.glob(os.path.join(LOCAL_REPOSITORY_DIR, "*tar*"))
    if len(filelist):
        subprocess.Popen(['rm'] + filelist)
    # cleans the cache dir
    run_pacman('-Sc')

def clean_db():
    filename = os.path.join(LOCAL_REPOSITORY_DIR, 'mod.db.tar.gz')
    if os.path.exists(filename):
        os.remove(filename)
def restart_services():
    def restart():
        subprocess.Popen(['systemctl', 'restart', 'mod-ui.service']).wait()
        sys.exit(0)
    ioloop.IOLoop.instance().add_timeout(time.time() + 0.5, restart)

def remove_lock():
    lockfile = '/var/lib/pacman/db.lck'
    if not os.path.exists(lockfile):
        return
    pidfile = '/tmp/pacman.pid'
    if not os.path.exists(pidfile):
        os.remove(lockfile)
        return
    pid = open('/tmp/pacman.pid').read().strip()
    try:
        pid = int(pid)
    except ValueError:
        os.remove(lockfile)
        return

    if os.path.exists('/proc/%d' % pid):
        # process is running
        # Something is really wrong. Let's just not take the risk to
        # cause a disaster by running pacman commands without knowing what's
        # happening. Let the user take the decision to reboot at worst case.
        time.sleep(1)
        sys.exit(1)
    os.remove(lockfile)


class RepositoryUpdate(fileserver.FileReceiver):
    """
    Receives a copy of the repository database and installs it locally
    """
    download_tmp_dir = DOWNLOAD_TMP_DIR
    remote_public_key = REPOSITORY_PUBLIC_KEY
    destination_dir = LOCAL_REPOSITORY_DIR

    def process_file(self, data, callback):
        self.file_callback = callback
        run_pacman('-Sy')
        self.result = True
        clean_db()
        self.file_callback()


class PackageDownload(fileserver.FileReceiver):
    """
    Just receive a package and saves at local repository
    """
    download_tmp_dir = DOWNLOAD_TMP_DIR
    remote_public_key = REPOSITORY_PUBLIC_KEY
    destination_dir = LOCAL_REPOSITORY_DIR

    def process_file(self, data, callback):
        self.result = True
        callback()

class BasePacmanRunner(web.RequestHandler):
    """
    This is a base web request handler that will:

    - make sure connection has not been closed when request starts
      ( this is very likely, since each pacman execution blocks everything )

    - set the Access-Control-Allow-Origin header, to allow the mod-ui server to access this one

    - call pacman_process, that will actually do what's needed

    - check again the connection, that might have been closed during pacman execution

    - write result and finish
    """
    @web.asynchronous # avoid automatic finish() call, that might be done in a closed connection
    def get(self, package_name=None):
        if self.request.connection.stream.closed():
            return
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('Origin', ''))
        result = self.pacman_process(package_name)
        if self.request.connection.stream.closed():
            return
        self.write(json.dumps(result))
        self.finish()

class ServiceStop(web.RequestHandler):
    def get(self):
        service = self.get_argument("service")
        run_systemctl_command('stop', service=service)
        self.redirect("/")

class ServiceStart(web.RequestHandler):
    def get(self):
        service = self.get_argument("service")
        run_systemctl_command('start', service=service)
        self.redirect("/")

class ServiceRestart(web.RequestHandler):
    def get(self):
        service = self.get_argument("service")
        run_systemctl_command('restart', service=service)
        self.redirect("/")

class RepositoryChange(web.RequestHandler):
    def get(self):
        repository = self.get_argument("repo")
        change_repo(repository)
        self.redirect("/")

class CloudChange(web.RequestHandler):
    def get(self):
        cloud = self.get_argument("cloud")
        change_cloud(cloud)
        self.redirect("/")

class UpgradeDependenciesList(BasePacmanRunner):
    """
    Based on local repository database, gets a list of all packages that are needed for upgrading installed packages
    (may include new dependencies)
    """
    def pacman_process(self, package_name):
        result = run_pacman('-Sup')
        packages = parse_pacman_output() if result else []

        if len(packages) == 0:
            clean_repo()

        return packages

class PackageDependenciesList(BasePacmanRunner):
    """
    Given a package, returns a list of all files that are needed to download (including the package itself
    and dependencies) to install it
    """
    def pacman_process(self, package_name):
        result = run_pacman('-Sp', package_name)
        packages = parse_pacman_output() if result else []

        if len(packages) == 0:
            clean_repo()

        return packages

class Upgrade(BasePacmanRunner):
    """
    Given that repository is updated and all new packages have been downloaded, upgrade
    all packages.
    """
    def pacman_process(self, package_name):
        result = run_pacman('-Su')
        clean_repo()
        restart_services()
        return result

class PackageInstall(BasePacmanRunner):
    """
    Given that all necessary files have been downloaded to local repository,
    install a package
    """
    def pacman_process(self, package_name):
        result = run_pacman('-S', package_name)
        clean_repo()
        restart_services()
        return result

class LastResult(BasePacmanRunner):
    """
    Since the pacman may block execution for a very long time,
    this handler provides a method for browser to know the result of
    the last pacman execution once it has ended, so that it can recover from
    an HTTP timeout.
    Returns boolean json
    """
    def pacman_process(self, package_name):
        result = open('/tmp/pacman.res').read()
        if len(result) == 0:
            # Something is really wrong, probably another process has messed with our result
            result = False
        else:
            result = int(result) == 0
        return result

class TemplateHandler(web.RequestHandler):
    def get(self, path):
        if self.request.connection.stream.closed():
            return
        if not path:
            path = 'index.html'
        loader = template.Loader(HTML_DIR)
        section = path.split('.')[0]
        try:
            context = getattr(self, section)()
        except AttributeError:
            context = {}
        context['repository'] = REPOSITORY_ADDRESS
        try:
            cloud_url = open("/root/cloud").read().strip()
        except IOError:
            cloud_url = "http://cloud.portalmod.com/"
        context['cloud'] = cloud_url

        self.write(loader.load(path).generate(**context))

    def index(self):
        context = {'services': {'mod-bluez':get_systemd_status('mod-bluez'),
                                'mod-ui':get_systemd_status('mod-ui'),
                                'mod-host':get_systemd_status('mod-host'),
                                'jackd':get_systemd_status('jackd')}}
        return context

class DemoReset(web.RequestHandler):
    """
    This is used for expomusic demo. It resets the IHM in case of hanging
    """
    def get(self):
        if not IHM_RESET_SCRIPT or not os.path.exists(IHM_RESET_SCRIPT):
            self.write("IHM reset disabled")
            return
        proc = subprocess.Popen(IHM_RESET_SCRIPT.split())
        proc.wait()
        if proc.poll() == 0:
            self.write("IHM reset ok")
        else:
            self.write("IHM script returned %d" % proc.poll())


application = web.Application(
    RepositoryUpdate.urls('system/update') +
    PackageDownload.urls('system/package/download') +
    [
        (r"/system/upgrade/dependencies/?$", UpgradeDependenciesList),
        (r"/system/upgrade/?$", Upgrade),
        (r"/system/package/dependencies/(.+)/?$", PackageDependenciesList),
        (r"/system/package/install/(.+)/?$", PackageInstall),
        (r"/system/result/?$", LastResult),
        (r"/system/stop/?$", ServiceStop),
        (r"/system/start/?$", ServiceStart),
        (r"/system/restart/?$", ServiceRestart),
        (r"/system/repository/?$", RepositoryChange),
        (r"/system/cloud/?$", CloudChange),
        (r"/([a-z]+\.html)?$", TemplateHandler),

        (r"/demo/reset/?$", DemoReset),

        (r"/(.*)", web.StaticFileHandler, {"path": HTML_DIR}),
        ],

    debug=True)

def run():
    def run_server():
        application.listen(PORT, address="0.0.0.0")
        options.parse_command_line()

    def check():
        check_environment()

    clean_db()
    run_server()
    ioloop.IOLoop.instance().add_callback(check)

    ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    run()
