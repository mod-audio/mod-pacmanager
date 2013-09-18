from setuptools import setup, find_packages
import os

setup(name = 'mod-pacmanager',
      version = '0.9.12',
      description = 'MOD ArchLinux Package Manager',
      long_description = 'MOD - Musician Operated Device - ArchLinux Package Manager',
      author = "Hacklab and AGR",
      author_email = "lhfagundes@hacklab.com.br",
      license = "GPLv3",
      packages = find_packages(),
      entry_points = {
          'console_scripts': [
              'mod-pacmanager = pacman.webserver:run',
              ]
          },
      scripts = [
      ],
      data_files = [("/usr/share/mod-pacmanager/", ['repository.pub'])],
      install_requires = ['tornado'],
      classifiers = [
          'Intended Audience :: Developers',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
        ],
      url = 'http://github.com/portalmod/mod-pacmanager',
)
