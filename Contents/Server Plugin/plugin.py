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
    if "debug" not in indigo.activePlugin.pluginPrefs:
      indigo.activePlugin.pluginPrefs["debug"] = True
    else:
      self.debugLog(u"Debug is set to: "+str(indigo.activePlugin.pluginPrefs["debug"]))
      self.debug = indigo.activePlugin.pluginPrefs["debug"]
    for dev in indigo.devices.iter("self"):
      if not dev.enabled or not dev.configured:
        continue
      if dev.deviceTypeId == u"verisureDeviceType":
        self.debugLog(u"Logging in")
        self.myPages = verisure.MyPages(dev.pluginProps["verisureUsername"], dev.pluginProps["verisurePassword"])
        self.myPages.login()


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
            self.debugLog(u"Checking status")
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
        self.sleep(15)
    except self.StopThread:
      pass  # Optionally catch the StopThread exception and do any needed cleanup.

  ########################################
  # Actions defined in MenuItems.xml:
  ####################
  def verisureGetUpdate(self):
    indigo.server.log(u"Update verisure State")

  def toggelDebug(self):
    if self.debug:
      self.debug = False
      indigo.activePlugin.pluginPrefs["debug"] = False
    else:
      self.debug = True
      indigo.activePlugin.pluginPrefs["debug"] = True
    self.debugLog(u"Debug is set to: "+str(self.debug))