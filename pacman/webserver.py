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

import json, subprocess, re, glob
import os
from tornado import web, gen, ioloop, options, template
from pacman import fileserver
from pacman.settings import check_environment

from pacman.settings import (DOWNLOAD_TMP_DIR, REPOSITORY_PUBLIC_KEY, LOCAL_REPOSITORY_DIR,
                             HTML_DIR, PORT, REPOSITORY_ADDRESS)

def run_command(command, callback):
    """
    Runs a command asynchronously inside a request and calls callback 
    passing subprocess object as parameter when finished
    """

    proc = subprocess.Popen(command,
                            stdout=subprocess.PIPE)
    loop = ioloop.IOLoop.instance()
    def check_process(fileno, event):
        if proc.poll() is None:
            return
        loop.remove_handler(fileno)
            
        callback(proc)

    loop.add_handler(proc.stdout.fileno(), check_process, 16)

def parse_pacman_output(output):
    """
    gets a pacman -S command output and retrieves a list of packages that it would install
    """
    return [ re.sub(r'.*://.*/', '', line) 
             for line in output.split() if "://" in line ]

def clean_repo():
    subprocess.Popen(['rm'] + glob.glob(os.path.join(LOCAL_REPOSITORY_DIR, "*tar*")))
def clean_db():
    filename = os.path.join(LOCAL_REPOSITORY_DIR, 'mod.db.tar.gz')
    if os.path.exists(filename):
        os.remove(filename)

class RepositoryUpdate(fileserver.FileReceiver):
    """
    Receives a copy of the repository database and installs it locally
    """
    download_tmp_dir = DOWNLOAD_TMP_DIR
    remote_public_key = REPOSITORY_PUBLIC_KEY
    destination_dir = LOCAL_REPOSITORY_DIR

    def process_file(self, data, callback):
        self.file_callback = callback
        yield gen.Task(run_command, ['rm', '-f', '/var/lib/pacman/db.lck'])
        run_command(['pacman', '-Sy'], 
                    self.do_callback)

    def do_callback(self, proc):
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

class UpgradeDependenciesList(web.RequestHandler):
    """
    Based on local repository database, gets a list of all packages that are needed for upgrading installed packages
    (may include new dependencies)
    """
    @web.asynchronous
    @gen.engine
    def get(self):
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('Origin', ''))
        yield gen.Task(run_command, ['rm', '-f', '/var/lib/pacman/db.lck'])
        proc = yield gen.Task(run_command, ['pacman', '--noconfirm', '-Sup'])
        packages = parse_pacman_output(proc.stdout.read())

        if len(packages) == 0:
            clean_repo()
        
        self.write(json.dumps(packages))
        self.finish()

class PackageDependenciesList(web.RequestHandler):
    """
    Given a package, returns a list of all files that are needed to download (including the package itself
    and dependencies) to install it
    """
    @web.asynchronous
    @gen.engine
    def get(self, package_name):
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('Origin', ''))
        yield gen.Task(run_command, ['rm', '-f', '/var/lib/pacman/db.lck'])
        proc = yield gen.Task(run_command, ['pacman', '--noconfirm', '-Sp', package_name])
        packages = parse_pacman_output(proc.stdout.read())

        if len(packages) == 0:
            clean_repo()
        
        self.write(json.dumps(packages))
        self.finish()

class Upgrade(web.RequestHandler):
    """
    Given that repository is updated and all new packages have been downloaded, upgraded
    all packages.
    """
    @web.asynchronous
    @gen.engine
    def get(self):
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('Origin', ''))
        yield gen.Task(run_command, ['rm', '-f', '/var/lib/pacman/db.lck'])
        proc = yield gen.Task(run_command, ['pacman', '--noconfirm', '-Su'])
        clean_repo()

        self.write(json.dumps(True))
        self.finish()

class PackageInstall(web.RequestHandler):
    """
    Given that all necessary files have been downloaded to local repository,
    install a package
    """
    @web.asynchronous
    @gen.engine
    def get(self, package_name):
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('Origin', ''))
        yield gen.Task(run_command, ['rm', '-f', '/var/lib/pacman/db.lck'])
        proc = yield gen.Task(run_command, ['pacman', '--noconfirm', '-S', package_name])
        clean_repo()
        self.write(json.dumps(True))
        self.finish()

class TemplateHandler(web.RequestHandler):
    def get(self, path):
        if not path:
            path = 'index.html'
        loader = template.Loader(HTML_DIR)
        section = path.split('.')[0]
        try:
            context = getattr(self, section)()
        except AttributeError:
            context = {}
        context['repository'] = REPOSITORY_ADDRESS
        self.write(loader.load(path).generate(**context))

    def index(self):
        context = {}
        return context


application = web.Application(
    RepositoryUpdate.urls('system/update') + 
    PackageDownload.urls('system/package/download') + 
    [
        (r"/system/upgrade/dependencies/?$", UpgradeDependenciesList),
        (r"/system/upgrade/?$", Upgrade),
        (r"/system/package/dependencies/(.+)/?$", PackageDependenciesList),
        (r"/system/package/install/(.+)/?$", PackageInstall),
        (r"/([a-z]+\.html)?$", TemplateHandler),
        
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
