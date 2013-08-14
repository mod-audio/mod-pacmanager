import os

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

DOWNLOAD_TMP_DIR = os.path.join(ROOT, 'tmp')
REPOSITORY_PUBLIC_KEY = os.path.join(ROOT, 'repository.pub')
LOCAL_REPOSITORY_DIR = '/pkgs' 
HTML_DIR = '/usr/share/mod-pacmanager/html/'
REPOSITORY_ADDRESS = 'packages.portalmod.com'
PORT = 8889

def check_environment():
    for dirname in (DOWNLOAD_TMP_DIR, LOCAL_REPOSITORY_DIR):
        if not os.path.exists(dirname):
            os.mkdir(dirname)
