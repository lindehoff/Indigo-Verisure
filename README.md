#Verisure plugin for Indigo
[Indigo](http://www.perceptiveautomation.com/indigo/index.html) plugin - get status for you Verisure Alarm and devices.

## Requirements

1. [Indigo 6](http://www.perceptiveautomation.com/indigo/index.html) or later (pro version only)
2. [requests module for python 2.6](http://docs.python-requests.org/)
3. [Verisure Alarm System](http://www.verisure.com)
4. Verisure [User account](https://mypages.verisure.com)

## Installation Instructions

1. Install requests, see details below
2. Download latest release [here](hhttps://github.com/lindehoff/Indigo-Verisure/releases)
3. Follow [standard plugin installation process](http://bit.ly/1e1Vc7b)

### Installing requests module
```
sudo easy_install-2.6 pip
sudo easy_install-2.6 pip requests
```

## Actions Supported
* Update Lock Status (Lock and Unlock)

## Devices Supported
* Verisure alarm (Read only in this version)
* Climate devices (Only Temperature in this release)
* Smart Locks
* Mice Detector

## Special thanks
Without [Per Sandström](https://github.com/persandstrom)s [Verisure Python](https://github.com/persandstrom/python-verisure) script this plugin could not exists.
