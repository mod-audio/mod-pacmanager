#!/usr/bin/env python

# FOR DEVELOPMENT PURPOSES ONLY

import os, sys

sys.path = [ os.path.dirname(os.path.realpath(__file__)) ] + sys.path

from pacman import webserver

webserver.run()
