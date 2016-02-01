#Verisure plugin for Indigo
[Indigo](http://www.perceptiveautomation.com/indigo/index.html) plugin - get status for you Verisure Alarm and devices.

## Requirements

1. [Indigo 6](http://www.perceptiveautomation.com/indigo/index.html) or later (pro version only)
2. [Verisure Python Module](https://pypi.python.org/pypi/vsure)
3. [Verisure Alarm System](http://www.verisure.com)
4. Verisure [User account](https://mypages.verisure.com)

## Installation Instructions

1. Install requests, see details below
2. Download latest release [here](hhttps://github.com/lindehoff/Indigo-Verisure/releases)
3. Follow [standard plugin installation process](http://bit.ly/1e1Vc7b)

### Installing Verisure module
```
sudo pip2.6 install vsure
```

## Actions Supported
* Update Lock Status (Lock and Unlock)
* Update Alarm Status (Arm (Home and Away) and Disarm)

## Devices Supported
* Verisure alarm
* Climate devices (Only Temperature in this release)
* Smart Locks
* Mice Detector

## Special thanks
Without [Per Sandström](https://github.com/persandstrom)s [Verisure Python](https://github.com/persandstrom/python-verisure) script this plugin could not exists.

## Legal Disclaimer
This plugin is not affiliated with Verisure Holding AB and the developers take no legal responsibility for the functionality or security of your Verisure Alarms and devices.
