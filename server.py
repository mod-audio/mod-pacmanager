#!/usr/bin/env python

# FOR DEVELOPMENT PURPOSES ONLY

import os, sys
ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path = [ ROOT ] + sys.path

from pacman import settings

if os.path.exists(os.path.join(ROOT, 'settings_local.py')):
    execfile(os.path.join(ROOT, 'settings_local.py'))

from pacman import webserver

webserver.run()
