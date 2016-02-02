#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo
import re
import os
import sys
import time
from datetime import datetime, timedelta
import verisure
import json
from ghpu import GitHubPluginUpdater
import traceback

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
  ########################################
  def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
    indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
    self.debug = True
    timeNow = time.time()
    self.nextCheck = timeNow - 86400
    self.updater = GitHubPluginUpdater('lindehoff', 'Indigo-Verisure', self)
    self.tryingToLogin = False
    self.loginErrorCount = 0
    self.currentSleepTime = int(self.pluginPrefs.get('updateRate', 300))


  def __del__(self):
    indigo.PluginBase.__del__(self)

  ########################################
  def startup(self):
    self.debugLog(u"startup called")
    if "debug" not in indigo.activePlugin.pluginPrefs:
      indigo.activePlugin.pluginPrefs["debug"] = True
    else:
      self.debugLog(u"Debug is set to: "+str(indigo.activePlugin.pluginPrefs["debug"]))
      self.debug = indigo.activePlugin.pluginPrefs["debug"]
    self.currentSleepTime = int(self.pluginPrefs.get('updateRate', 300))
    self.tryingToLogin = False
    self.loginErrorCount = 0

  def login(self, force=False):
    if not self.tryingToLogin or force:
      if "verisureUsername" not in self.pluginPrefs or "verisurePassword" not in self.pluginPrefs:
        self.errorLog(u"Must enter Username and Password in Plugin Config")
      else:
        self.tryingToLogin = True
        self.debugLog(u"Logging in")
        self.myPages = verisure.MyPages(self.pluginPrefs["verisureUsername"], self.pluginPrefs["verisurePassword"])
        self.myPages.login()
        self.debugLog(u"Logging in successfully.")
        if self.loginErrorCount > 0:
          indigo.server.log("Successfully connected to Verisure again")
        self.loginErrorCount = 0
        self.tryingToLogin = False

  def shutdown(self):
    self.debugLog(u"shutdown called")
    if hasattr(self, "myPages"):
      self.debugLog(u"Logging out")
      self.myPages.logout()

  def closedPrefsConfigUi(self, valuesDict, userCancelled):
    self.debugLog(u"Plugin config dialog window closed.")
    if userCancelled:
        self.debugLog(u"User prefs dialog cancelled.")
    if not userCancelled:
      try:
        self.currentSleepTime = 10
        if hasattr(self, "myPages"):
          self.debugLog(u"Logging out")
          self.myPages.logout()
        self.login(True)
      except Exception, e:
        self.errorLog(str(e))
    return

  ########################################
  # If runConcurrentThread() is defined, then a new thread is automatically created
  # and runConcurrentThread() is called in that thread after startup() has been called.
  #
  # runConcurrentThread() should loop forever and only return after self.stopThread
  # becomes True. If this function returns prematurely then the plugin host process
  # will log an error and attempt to call runConcurrentThread() again after several seconds.
  def runConcurrentThread(self):
    try:
      while True:
        # Did we check if there was an update within the last
        timeNow = time.time()
        # If the version wasn't checked within our time period then check
        if timeNow > self.nextCheck:
          self.updater.checkForUpdate()
          self.nextCheck = timeNow + 86400
        self.debugLog(u"Checking status for all Verisure Devices")
        for dev in indigo.devices.iter("self"):
          if not dev.enabled or not dev.configured:
            continue
          self._refreshAlarmStatesFromVerisure(dev)
        if not hasattr(self, "myPages"):
          self.debugLog(u"Currently not logged in, try again.")
          try:
            self.login()
          except Exception, e:
            self.loginErrorCount += 1
            if hasattr(self, "myPages"):
              delattr(self, "myPages")
            sleep = 60
            if "Too many failed login attempt" in str(e):
              sleep = 60*10
            elif type(e) == verisure.MaintenanceError:
              sleep = 120
            elif type(e) == verisure.LoggedOutError:
              sleep = 5
            sleep += (60 * self.loginErrorCount) - 60
            if self.loginErrorCount <=2:
              self.debugLog("{0}: Unable to login to Verisure ({1}), retry in {2} sec. Reason: {3}".format(type(e).__name__, self.loginErrorCount, sleep, e))
            else:
              self.errorLog("{0}: Unable to login to Verisure ({1}), retry in {2} sec. Reason: {3}".format(type(e).__name__, self.loginErrorCount, sleep, e))
            self.concurrentThreadSleep(sleep)
            self.tryingToLogin = False
            continue
        self.concurrentThreadSleep(int(self.pluginPrefs.get('updateRate', 300)))
    except self.StopThread:
      self.errorLog("StopThread")
      pass  # Optionally catch the StopThread exception and do any needed cleanup.

  def concurrentThreadSleep(self, sec):
    self.currentSleepTime = sec
    while self.currentSleepTime > 0:
      self.sleep(1)
      #self.debugLog("Sleeping for {0} sec.".format(self.currentSleepTime))
      self.currentSleepTime -= 1

  def _refreshAlarmStatesFromVerisure(self, dev):
    if hasattr(self, "myPages"):
      try:
        self.debugLog("Getting update for device: {0}".format(dev.name.encode("utf-8")))
        if dev.deviceTypeId == u"verisureAlarmDeviceType":
          verisureDeviceOverview = self.filterByValue(self.myPages.alarm.get(), "id", dev.pluginProps["alarmID"])
        elif dev.deviceTypeId == u"verisureDoorLockDeviceType":
          verisureDeviceOverview = self.filterByValue(self.myPages.lock.get(), "id", dev.pluginProps["doorLockID"])
        elif dev.deviceTypeId == u"verisureClimateDeviceType":
          verisureDeviceOverview = self.filterByValue(self.myPages.climate.get(), "id", dev.pluginProps["climateID"])
        elif dev.deviceTypeId == u"verisureMouseDetectionDeviceType":
          #return
          verisureDeviceOverview = self.filterByValue(self.myPages.mousedetection.get(), "deviceLabel", dev.pluginProps["mouseDetectiorID"])
      except (verisure.LoggedOutError, verisure.TemporarilyUnavailableError) as e:
        self.debugLog("{0}: Unable to update device state on server. Connection to Verisure will be reseted. Device: {1}, Reason: {2}".format(type(e).__name__, dev.name.encode("utf-8"), e))

        #Only during testing
        #self.errorLog("{0}: Unable to update device state on server. Connection to Verisure will be reseted. Device: {1}, Reason: {2}".format(type(e).__name__, dev.name.encode("utf-8"), e))
        delattr(self, "myPages")
        return
      except (verisure.MaintenanceError, verisure.LoginError, verisure.ResponseError, verisure.Error) as e:
        self.errorLog("{0}: Unable to update device state on server. Connection to Verisure will be reseted. Device: {1}, Reason: {2}".format(type(e).__name__, dev.name.encode("utf-8"), e))
        delattr(self, "myPages")
        return
      except Exception as e:
        template = "An exception of type {0} occured. \nArguments:\t{1!r}\nTraceback:\t{2!r}"
        message = template.format(type(e).__name__, e.args, traceback.format_exc())
        self.errorLog("Unknown Error: Unable to update device state on server. Device: {0}, Reason: {1}".format(dev.name.encode("utf-8"), message))
        delattr(self, "myPages")
        return

      for state in dev.states:
        if state in verisureDeviceOverview.__dict__:
          if state.encode("utf-8") == "date".encode("utf-8") or state.encode("utf-8") == "timestamp".encode("utf-8"):
            newState = self.createdDateString(verisureDeviceOverview.__dict__[state].encode("utf-8"))
          elif state.encode("utf-8") == "temperature".encode("utf-8"):
            temperature = verisureDeviceOverview.__dict__[state].encode("utf-8").replace("°","").replace(",",".")
            newState = (u"%.1f" % float(temperature))
          else:
            if type(verisureDeviceOverview.__dict__[state]) is str:
              newState = verisureDeviceOverview.__dict__[state].encode("utf-8")
            else:
              newState = verisureDeviceOverview.__dict__[state]
          if state in verisureDeviceOverview.__dict__ and dev.states[state] != newState:
            oldState = dev.states[state]
            dev.updateStateOnServer(state, value=newState)
            self.debugLog("Update state {0}: form {1} to {2} for {3}".format(state, oldState, newState, dev.name.encode("utf-8")))
          else:
            self.debugLog("{0}s state {1} has not changed, still set to {2}".format(dev.name.encode("utf-8"), state, newState))
      dev.updateStateOnServer("lastSynchronized", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
      self._updateDevUI(dev)
    else:
      self._updateDevUI(dev)


  def _updateDevUI(self, dev):
    lastUpdate = self.secSinceLastUpdate(dev)
    maxUpdateTime = int(self.pluginPrefs.get('updateRate', 15)) * 10
    if dev.deviceTypeId == u"verisureAlarmDeviceType":
      if lastUpdate > maxUpdateTime:
        self.debugLog("{0} sec. since last update for device: {1}".format(lastUpdate, dev.name.encode("utf-8")))
        dev.updateStateOnServer("status", value=u"unknown")

      #Setting correct icon
      if dev.states['status'] == u"armed":
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
      elif dev.states['status'] == u"armedhome":
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
      elif dev.states['status'] == u"unarmed":
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
      elif dev.states['status'] == u"pending":
        dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
      else:
        dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
    elif dev.deviceTypeId == u"verisureDoorLockDeviceType":
      if lastUpdate > maxUpdateTime:
        self.debugLog("{0} sec. since last update for device: {1}".format(lastUpdate, dev.name.encode("utf-8")))
        dev.updateStateOnServer("status", value=u"pending")

      #Setting correct icon
      if dev.states['status'] == u"locked":
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
      elif dev.states['status'] == u"unlocked":
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
      elif dev.states['status'] == u"pending":
        dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
      else:
        dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
    elif dev.deviceTypeId == u"verisureClimateDeviceType":
      if lastUpdate > maxUpdateTime:
        self.debugLog("{0} sec. since last update for device: {1}".format(lastUpdate, dev.name.encode("utf-8")))
        dev.updateStateOnServer('sensorValue', value=0, uiValue=u"{0} sec. since last update".format(lastUpdate))
        dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
      else:
        dev.updateStateOnServer('sensorValue', value=float(dev.states['temperature']), uiValue=str(dev.states['temperature']))
        dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
    elif dev.deviceTypeId == u"verisureMouseDetectionDeviceType":
      if lastUpdate > maxUpdateTime:
        self.debugLog("{0} sec. since last update for device: {1}".format(lastUpdate, dev.name.encode("utf-8")))
        dev.updateStateOnServer('sensorValue', value=0, uiValue=u"{0} sec. since last update".format(lastUpdate))
        dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
      else:
        if int(dev.states['count']) > 0:
          dev.updateStateOnServer('onOffState', True)
          dev.updateStateImageOnServer(indigo.kStateImageSel.MotionSensorTripped)
        else:
          dev.updateStateOnServer('onOffState', False)
          dev.updateStateImageOnServer(indigo.kStateImageSel.MotionSensor)
        dev.updateStateOnServer('sensorValue', value=int(dev.states['count']), uiValue=dev.states['amountText'].encode("utf-8"))

  def secSinceLastUpdate(self, dev):
    try:
      lastUpdate = datetime.now() - datetime.strptime(dev.states['lastSynchronized'], "%Y-%m-%d %H:%M:%S")
      seconds = lastUpdate.seconds
    except Exception, e:
      #This will happen when dev.states['lastSynchronized'] is not set
      self.debugLog("Unable to convert '{0}' to a datetime object".format(dev.states['lastSynchronized']))
      seconds = 0
    return seconds

  def filterByValue(self, items, attribute, value):
    for item in items:
      #indigo.server.log("{0}".format(str(item.__dict__)))
      if str(item.__dict__[attribute]) == str(value.encode("utf-8")):
        return item
    raise Exception("Item with attribute {0} set to {1} not found in {2}".format(attribute, value, items))

  def getVerisureDeviceList(self, filter="all", typeId=0, valuesDict=None, targetId=0):
    if(filter == "lock"):
      overviews = self.myPages.lock.get()
    elif(filter == "alarm"):
      overviews = self.myPages.alarm.get()
    elif(filter == "climate"):
      overviews = self.myPages.climate.get()
    elif(filter == "mousedetection"):
      overviews = self.myPages.mousedetection.get()
    else:
      raise Exception("Filter {0} not implemented".format(filter))
    deviceList = []
    for overview in overviews:
      if hasattr(overview, "id") and hasattr(overview, "location"):
        deviceList = deviceList + [(overview.id, overview.location)]
      elif hasattr(overview, "id") and hasattr(overview, "_overview_type"):
        deviceList = deviceList + [(overview.id, "{0} #{1}".format(overview._overview_type, overview.id))]
      elif hasattr(overview, "deviceLabel"):
        deviceList = deviceList + [(overview.deviceLabel, overview.location)]
    return sorted(deviceList)

  def updateLockStatus(self, pluginAction, dev):
    lock = dev.pluginProps['doorLockID']
    pin = self.substituteVariable(pluginAction.props.get("userPin"), validateOnly=False)
    state = pluginAction.props['new_status']

    if hasattr(self, "myPages"):
      try:
        self.debugLog("Trying to update lock '{0}' to {1}".format(dev.states["location"], state))
        sentStatus = self.myPages.lock.set(pin, lock, state)
        if sentStatus:
          response = self.myPages.alarm.wait_while_pending()
          if type(response) is int and response >= 0:
            indigo.server.log(u"Updated Lock State: "+state)
          elif "vector" in response:
            self.errorLog(response["vector"][0]["message"])
          else:
            self.errorLog(u"Unable to updated Lock State, response: {0}".format(response))
        else:
          self.errorLog(u"Unable to updated Lock State, event not sent, most likely your lock is already set to: {0}".format(state))
      except Exception, e:
        self.errorLog(str(e) + u", Unable to change lock state")
        template = "An exception of type {0} occured. \nArguments:\t{1!r}\nTraceback:\t{2!r}"
        message = template.format(type(e).__name__, e.args, traceback.format_exc())
        self.errorLog("{1}".format(message))

    else:
      self.debugLog(u"Currently not logged in, try again.")
      self.currentSleepTime = 1

  def updateAlarmStatus(self, pluginAction, dev):
    # alarm = dev.pluginProps['alarmID'] # multiple alarms is not currently supported
    pin = self.substituteVariable(pluginAction.props.get("userPin"), validateOnly=False)
    state = pluginAction.props['new_status']

    if hasattr(self, "myPages"):
      try:
        self.debugLog("Trying to update alarm state to {0}".format(state))
        sentStatus = self.myPages.alarm.set(pin, state)
        if sentStatus:
          response = self.myPages.alarm.wait_while_pending()
          if type(response) is int and response >= 0:
            indigo.server.log(u"Updated Alarm State: "+state)
          elif "vector" in response:
            self.errorLog(response["vector"][0]["message"])
          else:
            self.errorLog(u"Unable to updated Alarm State")
        else:
          self.errorLog(u"Unable to updated Alarm State, event not sent, most likely your alarm is already set to: {0}".format(state))
      except Exception, e:
        self.errorLog(str(e) + u", Unable to change alarm state")
    else:
      self.debugLog(u"Currently not logged in, try again.")
      self.currentSleepTime = 1

  def createdDateString(self, dateStr):
    try:
      dt = str(datetime.strptime(dateStr, "%m/%d/%y %I:%M %p"))
      return dt
    except Exception, e:
      if "today" in dateStr.lower():
        date = datetime.today().strftime("%Y-%m-%d ")
      elif "yesterday" in dateStr.lower():
        date = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d ")
      else:
        return dateStr
      m = re.search('(0?[1-9]|1[012])(:[0-5]\d) [APap][mM]', dateStr)
      if m:
        time = m.group(0)
        dt = str(datetime.strptime(date+time, '%Y-%m-%d %I:%M %p'))
        return dt
      else:
        return dateStr

  def toggelDebug(self):
    if self.debug:
      self.debug = False
      indigo.activePlugin.pluginPrefs["debug"] = False
    else:
      self.debug = True
      indigo.activePlugin.pluginPrefs["debug"] = True
    indigo.server.log(u"Debuging is set to: "+str(self.debug))

  ########################################
  # Sensor Action callback
  ######################
  def actionControlSensor(self, action, dev):
    ###### TURN ON ######
    # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
    if action.sensorAction == indigo.kSensorAction.TurnOn:
      indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "on"))
      # But we could request a sensor state update if we wanted like this:
      # dev.updateStateOnServer("onOffState", True)

    ###### TURN OFF ######
    # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
    elif action.sensorAction == indigo.kSensorAction.TurnOff:
      indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "off"))
      # But we could request a sensor state update if we wanted like this:
      # dev.updateStateOnServer("onOffState", False)

    ###### TOGGLE ######
    # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
    elif action.sensorAction == indigo.kSensorAction.Toggle:
      indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "toggle"))
      # But we could request a sensor state update if we wanted like this:
      # dev.updateStateOnServer("onOffState", not dev.onState)

  ########################################
  # General Action callback
  ######################
  def actionControlGeneral(self, action, dev):
    ###### BEEP ######
    if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
      # Beep the hardware module (dev) here:
      # ** IMPLEMENT ME **
      indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

    ###### STATUS REQUEST ######
    elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
      # Query hardware module (dev) for its current status here:
      # ** IMPLEMENT ME **
      indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))
      self._refreshAlarmStatesFromVerisure(dev)

  def checkForUpdates(self):
    indigo.server.log(u"Manually checking for updates")
    self.updater.checkForUpdate()

  def updatePlugin(self):
    self.updater.update()
