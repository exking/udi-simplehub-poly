# UDI Polyglot v2 SimpleControl Poly 

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-simplehub-poly/blob/master/LICENSE)
[![Build Status](https://travis-ci.org/exking/udi-simplehub-poly.svg?branch=master)](https://travis-ci.org/exking/udi-simplehub-poly)

This Poly provides an interface between [SimpleControl](https://www.simplecontrol.com) and [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2) server.
It's based on [API version 3.5](https://www.simplecontrol.com/wp-content/uploads/2016/05/HTTPCommandInterface.pdf) and is capable of switching activities in rooms and sending a limited number of commands to devices. There is no way of knowing what activity is currently running or device state, so it's a one-way interface only - ISY to SimpleControl.

### Installation instructions

You can install it from the Polyglot store or manually running
```
cd ~/.polyglot/nodeservers
git clone https://github.com/exking/udi-simplehub-poly.git SimpleControl
cd SimpleControl
./install.sh
```

### Configuration

Once installed - make sure your SimpleHub is set to "Allow command from external systems", then go to the node server configuration on the Polyglot web interface and create a custom parameter named `hubip`. Value should contain an IP address of the device you run SimpleHub on.

### Notes

Poly assumes that SimpleHub IP address never change, so it is recommended that you create an IP address reservation for SimpleHub device on your router.

Please report any problems on the UDI user forum.

Thanks and good luck.
