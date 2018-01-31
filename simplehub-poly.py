#!/usr/bin/env python3

import polyinterface
import sys
import os
import http.client
import re
import time
import json

from converters import id_2_addr
from prof_template import write_profile

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'SimpleHome'
        self.address = 'simplhomectrl'
        self.primary = self.address
        self.hub_conn = None
        self.hub_ip = None
        self.hub_conn_last_used = int(time.time())
        self.data = { 'rooms': {} }

    def start(self):
        LOGGER.info('Started SimpleHub controller')
        self.removeNoticesAll()
        if 'hubip' not in self.polyConfig['customParams']:
            self.addNotice('Please create a custom configuration parameter "hubip" and assign it your SimpleHub IP address')
        else:
            self.hub_ip = self.polyConfig['customParams']['hubip']
            self.discover()

    def _connect(self):
        if self.hub_ip is None:
            return False
        self.hub_conn_last_used = int(time.time())
        if self.hub_conn is None:
            if 'use_ssl' in self.polyConfig['customParams']:
                try:
                    self.hub_conn = http.client.HTTPSConnection(self.hub_ip, 47148)
                except Exception as e:
                    LOGGER.error('SimpleHub SSL connection problem: {}'.format(e))
                    return False
            else:
                try:
                    self.hub_conn = http.client.HTTPConnection(self.hub_ip, 47147)
                except Exception as e:
                    LOGGER.error('SimpleHub connection problem: {}'.format(e))
                    return False
        return True

    def _disconnect(self):
        if self.hub_conn is not None:
            self.hub_conn.close()
            self.hub_conn = None

    def run_activity(self, actid):
        if len(actid) == 0:
            LOGGER.error('Empty Activity UUID')
            return False
        if self._connect() is False:
            return False
        payload = { 'activity_uuid': actid }
        headers = { 'content-type': 'application/x-www-form-urlencoded' }
        try:
            self.hub_conn.request("POST", "/api/v1/runactivity", json.dumps(payload), headers)
        except Exception as e:
            LOGGER.error('SimpleHub connection problem: {}'.format(e))
            return False
        res = self.hub_conn.getresponse()
        rsp_data = res.read().decode("utf-8")
        if res.status == 200:
            LOGGER.debug('Set activity ok: {}'.format(rsp_data))
            self._disconnect()
            return True
        else:
            LOGGER.error('Set activity failed: {}'.format(rsp_data))
            self._disconnect()
            return False

    def send_command(self, devid, command):
        if self._connect() is False:
            return False
        payload =   {
                        'commands': [
                            {
                                'type': 'command',
                                'params': {
                                    'command': command,
                                    'device': devid
                                }
                            }
                        ]
                    }
        headers = { 'content-type': 'application/x-www-form-urlencoded' }
        try:
            self.hub_conn.request("POST", "/api/v1/sendcommands", json.dumps(payload), headers)
        except Exception as e:
            LOGGER.error('SimpleHub connection problem: {}'.format(e))
            return False
        res = self.hub_conn.getresponse()
        rsp_data = res.read().decode("utf-8")
        if res.status == 200:
            LOGGER.debug('Send command ok: {}'.format(rsp_data))
            self._disconnect()
            return True
        else:
            LOGGER.error('Send command failed: {}'.format(rsp_data))
            self._disconnect()
            return False

    def discover(self, command=None):
        if self._connect() is False:
            return False
        profile_upload = False
        if self._getActivities() is False:
            return False
        if self._getDevices() is False:
            return False
        LOGGER.debug('Discovery is complete.')
        self._disconnect()

        if 'customData' in self.polyConfig:
            if 'profile_done' in self.polyConfig['customData'] and self.polyConfig['customData']['profile_done']:
                LOGGER.info('Looks like we can skip the profile build')
            else:
                LOGGER.info('Writing out a new profile.zip')
                profile_upload = True
        else:
            profile_upload = True

        if command is not None:
            cmd = command.get('cmd')
            if cmd == 'DISCOVER':
                profile_upload = True

        if profile_upload:
            write_profile(self.data)
            self.poly.installprofile()
            cdata = { 'profile_done': True }
            self.saveCustomData(cdata)
            LOGGER.info('Profile upload to ISY is complete, please reboot ISY when possible')

        LOGGER.debug('Adding nodes to ISY')
        for room_id, rdata in self.data['rooms'].items():
            rnodedef = 'ROOM'+str(rdata['index'])
            raddress = id_2_addr(room_id)
            LOGGER.info('Room[{}]: {}'.format(rdata['index'], rdata['name']))
            if raddress not in self.nodes:
                self.addNode(SCRoom(self, raddress, raddress, rdata['name'], room_id, rnodedef, rdata))
            for act_id, act_data in rdata['activities'].items():
                LOGGER.info('Activity[{}]: {}'.format(act_data['index'], act_data['name']))
            for dev_id, dev_data in rdata['devices'].items():
                LOGGER.info('Device: {} ({})'.format(dev_data['name'], dev_data['type']))
                dev_address = id_2_addr(dev_id)
                if dev_address not in self.nodes and dev_data['type'] != 'Automate':
                    self.addNode(SCDevice(self, raddress, dev_address, dev_data['name'], dev_id, dev_data))

    def _getActivities(self):
        # Get Activities
        try:
            self.hub_conn.request("GET", "/api/v1/activities")
        except Exception as e:
            LOGGER.error('SimpleHub connection problem: {}'.format(e))
            return False
        res = self.hub_conn.getresponse()
        if res.status != 200:
            LOGGER.error('SimpleHub: activities - invalid response: {}'.format(res.status))
            return False
        try:
            activities = json.loads(res.read().decode("utf-8"))
        except:
            LOGGER.error('SimpleHub: unable to decode the activities response')
            return False
        # Start preparing our main work structure - self.data
        roomindex = 0
        actindex = {}
        for activity in activities['data']:
            m = re.split(': ', activity['name'])
            roomname = m[0]
            actname = m[1]
            if activity['roomuuid'] not in self.data['rooms']:
                room = {
                        'name': roomname,
                        'activities': {},
                        'devices': {},
                        'index': roomindex
                }
                roomindex += 1
                self.data['rooms'][activity['roomuuid']] = room
                actindex[activity['roomuuid']] = 1
            if activity['uuid'] not in self.data['rooms'][activity['roomuuid']]['activities']:
                act = {
                        'name': actname,
                        'index': actindex[activity['roomuuid']]
                }
                actindex[activity['roomuuid']] += 1
                self.data['rooms'][activity['roomuuid']]['activities'][activity['uuid']] = act
        return True

    def _getDevices(self):
        # Get Devices
        try:
            self.hub_conn.request("GET", "/api/v1/devices")
        except Exception as e:
            LOGGER.error('SimpleHub connection problem: {}'.format(e))
            return False
        res = self.hub_conn.getresponse()
        if res.status != 200:
            LOGGER.error('SimpleHub: devices - invalid response: {}'.format(res.status))
            return False
        try:
            devices = json.loads(res.read().decode("utf-8"))
        except:
            LOGGER.error('SimpleHub: unable to decode the devices response')
            return False
        for device in devices['data']:
            if device['uuid'] not in self.data['rooms'][device['roomuuid']]['devices']:
                dev = {
                        'name': device['name'],
                        'type': device['type']
                }
                self.data['rooms'][device['roomuuid']]['devices'][device['uuid']] = dev
        return True

    def stop(self):
        LOGGER.debug('SimpleHub NodeServer is shutting down')
        self._disconnect()

    def shortPoll(self):
        for node in self.nodes:
            self.nodes[node].updateInfo()
            
    def updateInfo(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def longPoll(self):
        pass
        '''
        if self.hub_conn is not None:
            if (int(time.time()) - self.hub_conn_last_used) > 300:
                self._disconnect()
        '''

    id = 'SMPLHUB'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


class SCRoom(polyinterface.Node):
    def __init__(self, controller, primary, address, name, uuid, id, data):
        super().__init__(controller, primary, address, name)
        self.id = id
        self.uuid = uuid
        self.st = 0

    def start(self):
        try:
            self.st = int(self.getDriver('ST'))
        except:
            self.st = 1
        self.updateInfo()

    def updateInfo(self):
        self.setDriver('ST', self.st)

    def query(self):
        self.updateInfo()
        self.reportDrivers()

    def setActivity(self, command):
        self.st = int(command.get('value'))
        auuid = self._findActUUID(self.st)
        self.controller.run_activity(auuid)
        self.setDriver('ST', self.st)

    def _findActUUID(self, idx):
        for act_id, act_data in self.controller.data['rooms'][self.uuid]['activities'].items():
            if act_data['index'] == idx:
                return act_id
        return ''

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}
              ]
    id = 'ROOMn'
    commands = {
                    'SET_ACTIVITY': setActivity
               }


class SCDevice(polyinterface.Node):
    def __init__(self, controller, primary, address, name, uuid, data):
        super().__init__(controller, primary, address, name)
        self.st = 0
        self.uuid = uuid

    def start(self):
        try:
            self.st = int(self.getDriver('ST'))
        except:
            self.st = 1
        self.updateInfo()

    def updateInfo(self):
        self.setDriver('ST', self.st)

    def query(self):
        self.updateInfo()
        self.reportDrivers()

    def setPower(self, command):
        cmd = command.get('cmd')
        if cmd == 'DON':
            self.controller.send_command(self.uuid, 'POWER ON')
            self.st = 2
        elif cmd == 'DOF':
            self.controller.send_command(self.uuid, 'POWER OFF')
            self.st = 3
        elif cmd == 'PTOGGLE':
            self.controller.send_command(self.uuid, 'POWER TOGGLE')
            self.st = 4
        else:
            LOGGER.error('Invalid command: {}'.format(cmd))
        self.setDriver('ST', self.st)

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}
              ]
    id = 'DEVICE'
    commands = {
                    'DON': setPower, 'DOF': setPower, 'PTOGGLE': setPower
               }


if __name__ == "__main__":
    if not os.path.exists('profile.zip'):
        write_profile()
    try:
        polyglot = polyinterface.Interface('SimpleControl')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
