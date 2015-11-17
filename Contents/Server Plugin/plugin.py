#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time
sys.path.insert(0, '../Includes/python-verisure')
import verisure

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
    if "verisureUsername" not in self.pluginPrefs or "verisurePassword" not in self.pluginPrefs:
      self.debugLog(u"Must enter Username and Password in Plugin Config")
    else:
      self.debugLog(u"Logging in")
      self.myPages = verisure.MyPages(self.pluginPrefs["verisureUsername"], self.pluginPrefs["verisurePassword"])
      self.myPages.login()
    if "debug" not in indigo.activePlugin.pluginPrefs:
      indigo.activePlugin.pluginPrefs["debug"] = True
    else:
      self.debugLog(u"Debug is set to: "+str(indigo.activePlugin.pluginPrefs["debug"]))
      self.debug = indigo.activePlugin.pluginPrefs["debug"]


  def shutdown(self):
    self.debugLog(u"shutdown called")
    for dev in indigo.devices.iter("self"):
      if not dev.enabled or not dev.configured:
        continue
      if dev.deviceTypeId == u"verisureDeviceType":
        self.debugLog(u"Logging out")
        self.myPages.logout()

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
        for dev in indigo.devices.iter("self"):
          if not dev.enabled or not dev.configured:
            continue
          if dev.deviceTypeId == u"verisureDeviceType":
            self.debugLog(u"Checking status for " + dev.name)
            try:
              alarm_overview = self.myPages.get_overview(verisure.MyPages.DEVICE_ALARM)
            except Exception, e:
              self.debugLog(u"Error, trying to relogging in")
              try:
                self.myPages.logout()
                self.myPages = verisure.MyPages(dev.pluginProps["verisureUsername"], dev.pluginProps["verisurePassword"])
                self.myPages.login()
              except Exception, e:
                self.debugLog(u"Unable to login, will try again in a while")
                self.sleep(60)

            dev.updateStateOnServer("status", value=alarm_overview[0].status)
            dev.updateStateOnServer("sensorValue", value=1, uiValue=alarm_overview[0].status)
            self.debugLog("{0} {1} by {2}".format(alarm_overview[0].label, alarm_overview[0].date, alarm_overview[0].name))
          elif dev.deviceTypeId == u"verisureAlarmDeviceType":
            self.debugLog(u"Checking status for " + dev.name)
            try:
              alarm_overview = self.myPages.get_overview(verisure.MyPages.DEVICE_ALARM)
            except Exception, e:
              self.debugLog(u"Error, trying to relogging in")
              try:
                self.myPages.logout()
                self.myPages = verisure.MyPages(self.pluginPrefs["verisureUsername"], self.pluginPrefs["verisurePassword"])
                self.myPages.login()
              except Exception, e:
                self.debugLog(u"Unable to login, will try again in a while")
                self.sleep(60)

            dev.updateStateOnServer("status", value=alarm_overview[0].status)
            dev.updateStateOnServer("name", value=alarm_overview[0].name)
            dev.updateStateOnServer("label", value=alarm_overview[0].label)
            dev.updateStateOnServer("date", value=alarm_overview[0].date)
            #dev.updateStateOnServer("sensorValue", value=1, uiValue=alarm_overview[0].status)
            self.debugLog("{0} {1} by {2}".format(alarm_overview[0].label, alarm_overview[0].date, alarm_overview[0].name))
          elif dev.deviceTypeId == u"verisureClimateDeviceType":
            climate_overviews = self.myPages.get_overview(verisure.MyPages.DEVICE_CLIMATE)
            for climate_overview in climate_overviews:
              if (climate_overview.location + " (" +climate_overview.id + ")") == dev.pluginProps["climateID"]:
                try:
                  temp = climate_overview.temperature.replace("°","").replace(",",".")
                  input_value = float(temp)
                  format_temp = u"%.1f"
                  input_value = (format_temp % input_value)
                  dev.updateStateOnServer('sensorValue', value=input_value, uiValue=input_value)
                  dev.updateStateOnServer('temperature', value=input_value, uiValue=input_value)
                  dev.updateStateOnServer('timestamp', value=climate_overview.timestamp, uiValue=climate_overview.timestamp)
                  self.debugLog("Update temp to: {0}".format(temp))
                except Exception, e:
                  self.debugLog(unicode("Unable to update device state on server. Device: %s, Reason: %s" % (dev.name, e)))
                  dev.updateStateOnServer('sensorValue', value=u"Unsupported", uiValue=u"Unsupported")
                  dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

                dev.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensorOn)
                dev.updateStateOnServer('onOffState', value=True, uiValue=" ")
        self.sleep(15)
    except self.StopThread:
      pass  # Optionally catch the StopThread exception and do any needed cleanup.
  def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
      """
      This method is called whenever a device config dialog is closed.
      If you call the wrong thing from here, for example, if you try
      to update a device before it's fully configured, you can make
      Indigo very angry.
      """
      self.debugLog(u'closedDeviceConfigUi() method called:')
      if userCancelled:
          self.debugLog(u"Device configuration cancelled.")
          return
      else:
          pass
  ########################################
  # Actions defined in MenuItems.xml:
  ####################
  def verisureGetUpdate(self):
    indigo.server.log(u"Update verisure State")

  def getClimateList(self, filter="indigo.sensor", typeId=0, valuesDict=None, targetId=0):
    self.debugLog(u"getClimateList() method called.")
    self.debugLog(u"Generating list of Climate sensors...")
    climate_overviews = self.myPages.get_overview(verisure.MyPages.DEVICE_CLIMATE)
    sensorID_list = []
    for climate_overview in climate_overviews:
      sensorID_list = sensorID_list + [(climate_overview.location + " (" +climate_overview.id + ")")]
    sortedSensorList = sorted(sensorID_list)
    return sortedSensorList

  def toggelDebug(self):
    if self.debug:
      self.debug = False
      indigo.activePlugin.pluginPrefs["debug"] = False
    else:
      self.debug = True
      indigo.activePlugin.pluginPrefs["debug"] = True
    self.debugLog(u"Debug is set to: "+str(self.debug))