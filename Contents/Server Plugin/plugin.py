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
sys.path.insert(0, '../Includes/python-verisure')
import verisure
import json

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
  ########################################
  def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
    indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
    self.debug = True

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

  def login(self):
    if "verisureUsername" not in self.pluginPrefs or "verisurePassword" not in self.pluginPrefs:
      self.errorLog(u"Must enter Username and Password in Plugin Config")
    else:
      self.debugLog(u"Logging in")
      self.myPages = verisure.MyPages(self.pluginPrefs["verisureUsername"], self.pluginPrefs["verisurePassword"])
      try:
        self.myPages.login()
      except Exception, e:
        if hasattr(self, "myPages"):
          delattr(self, "myPages")
        if "Too many failed login attempt" in str(e):
          self.errorLog(str(e) + u",Uable to login, will try again in 10 minutes")
          self.sleep(60*10)
        else:
          raise Exception('Error login in: ' + str(e)) 

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
        self.login()
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
        if hasattr(self, "myPages"):
          self.debugLog(u"Checking status for all Verisure Devices")
          try:
            verisure_overviews = self.myPages.get_overviews()
          except Exception, e:
            self.errorLog(str(e) + ", trying to relogging in")
            try:
              self.myPages.logout()
              self.login()
            except Exception, e:
              self.errorLog(str(e) + u",Unable to login, will try again in a while")
              self.sleep(60)
              continue
          for verisure_overview in verisure_overviews:
            if verisure_overview._overview_type == u"alarm" and verisure_overview.type == u"ARM_STATE":
              for dev in indigo.devices.iter("self"):
                if not dev.enabled or not dev.configured:
                  continue
                if dev.deviceTypeId == u"verisureAlarmDeviceType":
                  try:
                    dev.updateStateOnServer("status", value=verisure_overview.status)
                    dev.updateStateOnServer("name", value=verisure_overview.name)
                    dev.updateStateOnServer("label", value=verisure_overview.label)
                    dev.updateStateOnServer("date", value=self.createdDateString(verisure_overview.date))
                    #dev.updateStateOnServer("sensorValue", value=1, uiValue=verisure_overview.status)
                    if verisure_overview.status == u"armed":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
                    elif verisure_overview.status == u"armedhome":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    elif verisure_overview.status == u"unarmed":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    elif verisure_overview.status == u"pending":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
                    else:
                      dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
                    self.debugLog("Update {0}s state: {1} {2} by {3}".format(dev.name.encode("utf-8"), verisure_overview.label, verisure_overview.date, verisure_overview.name))
                  except Exception, e:
                    self.errorLog(unicode("Unable to update device state on server. Device: %s, Reason: %s" % (dev.name.encode("utf-8"), e)))
            elif verisure_overview._overview_type == u"lock" and verisure_overview.type == u"DOOR_LOCK":
              for dev in indigo.devices.iter("self"):
                if not dev.enabled or not dev.configured:
                  continue
                if dev.deviceTypeId == u"verisureDoorLockDeviceType":
                  try:
                    dev.updateStateOnServer("status", value=verisure_overview.status)
                    dev.updateStateOnServer("name", value=verisure_overview.name)
                    dev.updateStateOnServer("label", value=verisure_overview.label)
                    dev.updateStateOnServer("date", value=self.createdDateString(verisure_overview.date))
                    dev.updateStateOnServer("location", value=verisure_overview.location)
                    #dev.updateStateOnServer("sensorValue", value=1, uiValue=verisure_overview.status)
                    if verisure_overview.status == u"locked":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
                    elif verisure_overview.status == u"unlocked":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    elif verisure_overview.status == u"pending":
                      dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
                    else:
                      dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
                    self.debugLog("Update {0}s state: {1} {2} by {3}".format(dev.name.encode("utf-8"), verisure_overview.label, verisure_overview.date, verisure_overview.name))
                  except Exception, e:
                    self.errorLog(unicode("Unable to update device state on server. Device: %s, Reason: %s" % (dev.name.encode("utf-8"), e)))
            elif verisure_overview._overview_type == u"climate":
              for dev in indigo.devices.iter("self"):
                if not dev.enabled or not dev.configured:
                  continue
                if dev.deviceTypeId == u"verisureClimateDeviceType":
                  if (verisure_overview.location + " (" +verisure_overview.id + ")") == dev.pluginProps["climateID"].encode('utf-8'):
                    try:
                      temp = verisure_overview.temperature.replace("°","").replace(",",".")
                      input_value = float(temp)
                      format_temp = u"%.1f"
                      input_value = (format_temp % input_value)
                      dev.updateStateOnServer('sensorValue', value=input_value, uiValue=input_value)
                      dev.updateStateOnServer('temperature', value=input_value, uiValue=input_value)
                      dev.updateStateOnServer('timestamp', value=self.createdDateString(verisure_overview.timestamp), uiValue=self.createdDateString(verisure_overview.timestamp))
                      self.debugLog("Update {0}s temperature to: {1}".format(dev.name.encode("utf-8"), temp))
                      dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
                      dev.updateStateOnServer('onOffState', value=True, uiValue=" ")
                    except Exception, e:
                      self.errorLog(unicode("Unable to update device state on server. Device: %s, Reason: %s" % (dev.name.encode("utf-8"), e)))
                      dev.updateStateOnServer('sensorValue', value=u"Unsupported", uiValue=u"Unsupported")
                      dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
            elif verisure_overview._overview_type == u"mousedetection":
              for dev in indigo.devices.iter("self"):
                if not dev.enabled or not dev.configured:
                  continue
                if dev.deviceTypeId == u"verisureMouseDetectionDeviceType":
                  if (verisure_overview.location + " (" +verisure_overview.deviceLabel + ")") == dev.pluginProps["mouseDetectiorID"].encode('utf-8'):
                    try:
                      count = verisure_overview.count
                      input_value = int(count)
                      
                      dev.updateStateOnServer('count', value=input_value, uiValue=str(verisure_overview.amountText))
                      dev.updateStateOnServer('location', value=verisure_overview.location, uiValue=verisure_overview.location)
                      self.debugLog("Update {0}s mice to: {1}".format(dev.name.encode("utf-8"), input_value))
                      
                      dev.updateStateOnServer('onOffState', value=True, uiValue=" ")
                    except Exception, e:
                      self.errorLog(unicode("Unable to update device state on server. Device: %s, Reason: %s" % (dev.name.encode("utf-8"), e)))
                      dev.updateStateOnServer('sensorValue', value=u"Unsupported", uiValue=u"Unsupported")
                      dev.updateStateImageOnServer(indigo.kStateImageSel.Error)
            else:
              self.debugLog("Device type " + str(verisure_overview._overview_type) + " in not implemented yet.")
        else:
          self.debugLog(u"Currently not logged in, try again.")
          try:
              self.login()
          except Exception, e:
            self.errorLog(str(e) + u",Unable to login, will try again in a while")
            self.sleep(60)
            continue

        self.sleep(int(self.pluginPrefs.get('updateRate', 15)))
    except self.StopThread:
      pass  # Optionally catch the StopThread exception and do any needed cleanup.

  def getVerisureDeviceList(self, filter="all", typeId=0, valuesDict=None, targetId=0):
    overviews = self.myPages.get_overview(filter)
    deviceList = []
    for overview in overviews:
      if filter != "lock" or (filter == "lock" and overview.type == u"DOOR_LOCK"): 
        if hasattr(overview, "id"):
          deviceList = deviceList + [(overview.id, overview.location)]
        elif hasattr(overview, "deviceLabel"):
          deviceList = deviceList + [(overview.deviceLabel, overview.location)]
    return sorted(deviceList)
    
  def getClimateList(self, filter="indigo.sensor", typeId=0, valuesDict=None, targetId=0):
    self.debugLog(u"getClimateList() method called.")
    self.debugLog(u"Generating list of Climate sensors...")
    climate_overviews = self.myPages.get_overview(verisure.MyPages.DEVICE_CLIMATE)
    sensorID_list = []
    for climate_overview in climate_overviews:
      sensorID_list = sensorID_list + [(climate_overview.location + " (" +climate_overview.id + ")")]
    sortedSensorList = sorted(sensorID_list)
    return sortedSensorList

  def getMouseDetectiorList(self, filter="indigo.sensor", typeId=0, valuesDict=None, targetId=0):
    self.debugLog(u"getMouseDetectiorList() method called.")
    self.debugLog(u"Generating list of mouse detectiors...")
    mouseDetection_overviews = self.myPages.get_overview(verisure.MyPages.DEVICE_MOUSEDETECTION)
    sensorID_list = []
    for mouseDetection_overview in mouseDetection_overviews:
      sensorID_list = sensorID_list + [(mouseDetection_overview.location + " (" +mouseDetection_overview.deviceLabel + ")")]
    sortedSensorList = sorted(sensorID_list)
    return sortedSensorList

  def updateLockStatus(self, pluginAction, dev):
    lock = dev.pluginProps['doorLockID']
    pin = pluginAction.props['userPin']
    state = pluginAction.props['new_status']

    if hasattr(self, "myPages"):
      try:
        self.debugLog("Trying to update lock '{0}' to {1}".format(dev.states["location"], state))
        self.myPages.set_lock_status(pin, lock, state)
        response = self.myPages.wait_while_pending()
        if not response and "vector" in response:
          self.errorLog(response["vector"][0]["message"])
        elif response:
          self.debugLog(u"Updated Lock State: "+state)
        else:
          self.debugLog(u"Unable to updated Lock State")
      except Exception, e:
        self.errorLog(str(e) + u", Unable to change lock state")

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