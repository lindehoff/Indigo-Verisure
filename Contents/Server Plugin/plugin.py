#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time

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
		self.debugLog(u"startup called, test")


	def shutdown(self):
		self.debugLog(u"shutdown called")

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
				self.debugLog(u"Checking state")
				self.sleep(10)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	# Actions defined in MenuItems.xml:
	####################
	def verisureGetUpdate(self):
		indigo.server.log(u"Update verisure State")

	def toggelDebug(self):
		if self.debug:
			self.debug = False
		else:
			self.debug = True