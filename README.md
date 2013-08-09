mod-pacmanager
==============

Server to manage software upgrades through HTTP, inside MOD device.

Generally, this can be used in any project in which:

 - You have an Arch Linux
 - This Arch has no route to internet, but is connected to a computer in which a browser is available
 - You want to install and upgrade arch packages using the browser to connect the system to a package repository

In our particular case, we have a dedicated hardware running Arch, which is connected to a computer via bluetooth.
