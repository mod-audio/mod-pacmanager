#!/usr/bin/env python

# This is a sample of server that will run in the package server, that will send
# files to this mod-pacmanager server
#
# modcommon comes from mod-python package.
# Although the fileserver package is copied inside this repository, this server won't run in
# same environment
from modcommon.communication import fileserver

import os, tornado.web, tornado.options

# This configuration will be fine to run behind a proxy like nginx
ADDRESS = "127.0.0.1"
PORT = 8890
URI = '/api'

ROOT = os.path.dirname(os.path.realpath(__file__))

class PackageSender(fileserver.FileSender):
    # Path to package server private key. The embedded server will need public key to validate packages
    # By default, it's a package-key.pem in same directory as this file
    private_key = os.path.join(ROOT, 'package-key.pem')

    # The packages directory, by default "packages/" in same directory of this file
    base_dir = os.path.join(ROOT, 'packages/')

    # The cache directory, optional, by defaul "cache/" in same directory of this file
    cache_dir = os.path.join(ROOT, 'cache/')

application = tornado.web.Application(PackageSender.urls(URI))
application.listen(PORT, address=ADDRESS)
tornado.options.parse_command_line()
tornado.ioloop.IOLoop.instance().start()
