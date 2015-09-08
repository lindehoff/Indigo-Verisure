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
		self.timeWarpOn = False
		self.timeWarpCount = 0

	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.debugLog(u"startup called")

		# Most plugins that expose new device types will depend on the user
		# creating the new device from the Indigo UI (just like a native device).
		#
		# However, it is also possible for the plugin to create the devices
		# automatically at runtime:
		if "Example Server Time" in indigo.devices:
			self.serverTimeDev = indigo.devices["Example Server Time"]
		else:
			indigo.server.log(u"creating test device: Example Server Time")
			self.serverTimeDev = indigo.device.create(indigo.kProtocol.Plugin, "Example Server Time", "test device created by example plugin", deviceTypeId="serverTimeDevice")
		# Override the state icon shown (in Indigo Touch and client Main Window)
		# for this device to be the timer image icon:
		self.serverTimeDev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)

		if "Example State Updater" in indigo.devices:
			self.stateUpdaterDev = indigo.devices["Example State Updater"]
		else:
			indigo.server.log(u"creating test device: Example State Updater")
			self.stateUpdaterDev = indigo.device.create(indigo.kProtocol.Plugin, "Example State Updater", "test state value updating device created by example plugin device", deviceTypeId="stateUpdater")
		# Override the state icon shown (in Indigo Touch and client Main Window)
		# for this device to be the timer image icon:
		self.stateUpdaterDev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)

	def shutdown(self):
		self.debugLog(u"shutdown called")

		self.serverTimeDev.updateStateOnServer("serverTimeSeconds", 0)
		self.serverTimeDev.updateStateOnServer("serverSecondsEven", False)
		self.serverTimeDev.updateStateOnServer("serverDateTime", "--")

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
				if self.timeWarpOn:
					self.timeWarpCount += 1
					self.serverTimeDev.updateStateOnServer("serverTimeSeconds", self.timeWarpCount)
					self.serverTimeDev.updateStateOnServer("serverSecondsEven", not bool(self.timeWarpCount % 2))
					self.sleep(0.15)
				else:
					serverTime = indigo.server.getTime()
					self.serverTimeDev.updateStateOnServer("serverTimeSeconds", serverTime.second)
					self.serverTimeDev.updateStateOnServer("serverSecondsEven", not bool(serverTime.second % 2))
					self.serverTimeDev.updateStateOnServer("serverDateTime", str(serverTime))
					if serverTime.second % 2:
						self.stateUpdaterDev.updateStateOnServer("alwaysInteger", 0)
						self.stateUpdaterDev.updateStateOnServer("alwaysFloat", 0.01)
						self.stateUpdaterDev.updateStateOnServer("stringToggleFloats", "0.0")
						self.stateUpdaterDev.updateStateOnServer("stringToggleStrings", "abc")
						self.stateUpdaterDev.updateStateOnServer("integerToFloat", 0)
						self.stateUpdaterDev.updateStateOnServer("integerToString", 0)
						self.stateUpdaterDev.updateStateOnServer("floatToString", 0.1)
					else:
						self.stateUpdaterDev.updateStateOnServer("alwaysInteger", 1)
						self.stateUpdaterDev.updateStateOnServer("alwaysFloat", 0.123456, decimalPlaces=4)
						self.stateUpdaterDev.updateStateOnServer("stringToggleFloats", "0.0000")
						self.stateUpdaterDev.updateStateOnServer("stringToggleStrings", "def")
						self.stateUpdaterDev.updateStateOnServer("integerToFloat", 0.1)
						self.stateUpdaterDev.updateStateOnServer("integerToString", "abc")
						self.stateUpdaterDev.updateStateOnServer("floatToString", "abc")
					self.stateUpdaterDev.updateStateOnServer("timeStamp", str(time.time()).split(".")[0])
					self.sleep(1)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	# Actions defined in MenuItems.xml:
	####################
	def timeWarp(self):
		if not self.timeWarpOn:
			indigo.server.log(u"starting mega time warp")
			self.timeWarpOn = True
		else:
			indigo.server.log(u"stopping mega time warp")
			self.timeWarpOn = False

	########################################
	# Buttons and dynamic list methods defined for the scenes custom device
	#
	# Overview of scene devices:
	#	Scene devices are custom devices that will contain multiple devices.
	# 	We implement this custom device by storing a comma-delimited list of
	#	device IDs which is manipulated by clicking Add and Delete buttons
	#	in the device config dialog. There are two dynamic list controls in
	#	the dialog:
	#		1) one popup button control on which the user selects a device
	#		   to add then clicks the Add Device button.
	#		2) one list control which shows all the devices that have already
	#		   been added to the scene and in which the user can select devices
	#		   and click the Delete Devices button
	#	There is a hidden field "memberDevices" that stores a comma-delimited
	#	list of device ids for each member of the scene. The addDevice and
	#	deleteDevices methods will take the selections from the respective
	#	dynamic lists and do the right thing with the list.
	#	Finally, there are the two methods that build the dynamic lists.
	#	The method that builds the source list will inspect the "memberDevices"
	#	field and won't include those devices in the source list (so the user
	#	won't be confused by seeing a device that's already in the member list
	#	in the source list). The method that builds the member list of course
	#	uses "memberDevices" to build the list.
	#
	#	One other thing that should be done probably - in the deviceStartComm
	#	method (or the appropriate CRUD methods if you're using them instead)
	#	you should check the IDs to make sure they're still around and if not
	#	remove them from the device id list.
	#
	#	The device id list property ("memberDevices") could, of course, be
	#	formatted in some other way besides a comma-delimited list of ids
	#	if you need to store more information. You could, for instance, store
	#	some kind of formatted text like JSON or XML that had much more
	#	information.

	####################
	# This is the method that's called by the Add Device button in the scene
	# device config UI.
	####################
	def addDevice(self, valuesDict, typeId, devId):
		self.debugLog(u"addDevice called")
		# just making sure that they have selected a device in the source
		# list - it shouldn't be possible not to but it's safer
		if "sourceDeviceMenu" in valuesDict:
			# Get the device ID of the selected device
			deviceId = valuesDict["sourceDeviceMenu"]
			if deviceId == "":
				return
			# Get the list of devices that have already been added to the "scene"
			# If the key doesn't exist then return an empty string indicating
			# no devices have yet been added. "memberDevices" is a hidden text
			# field in the dialog that holds a comma-delimited list of device
			# ids, one for each of the devices in the scene.
			selectedDevicesString = valuesDict.get("memberDevices","")
			self.debugLog("adding device: %s to %s" % (deviceId, selectedDevicesString))
			# If no devices have been added then just set the selected device string to
			# the device id of the device they selected in the popup
			if selectedDevicesString == "":
				selectedDevicesString = deviceId
			# Otherwise append it to the end separated by a comma
			else:
				selectedDevicesString += "," + str(deviceId)
			# Set the device string back to the hidden text field that contains the
			# list of device ids that are in the scene
			valuesDict["memberDevices"] = selectedDevicesString
			self.debugLog("valuesDict = " + str(valuesDict))
			# Delete the selections on both dynamic lists since we don't
			# want to preserve those across dialog runs
			if "memberDeviceList" in valuesDict:
				del valuesDict["memberDeviceList"]
			if "sourceDeviceMenu" in valuesDict:
				del valuesDict["sourceDeviceMenu"]
			# return the new dict
			return valuesDict

	####################
	# This is the method that's called by the Delete Device button in the scene
	# device config UI.
	####################
	def deleteDevices(self, valuesDict, typeId, devId):
		self.debugLog(u"deleteDevices called")
		if "memberDevices" in valuesDict:
			# Get the list of devices that are already in the scene
			devicesInScene = valuesDict.get("memberDevices","").split(",")
			# Get the devices they've selected in the list that they want
			# to remove
			selectedDevices = valuesDict.get("memberDeviceList", [])
			# Loop through the devices to be deleted list and remove them
			for deviceId in selectedDevices:
				self.debugLog("remove deviceId: " + deviceId)
				if deviceId in devicesInScene:
					devicesInScene.remove(deviceId)
			# Set the "memberDevices" field back to the new list which
			# has the devices deleted from it.
			valuesDict["memberDevices"] = ",".join(devicesInScene)
			# Delete the selections on both dynamic lists since we don't
			# want to preserve those across dialog runs
			if "memberDeviceList" in valuesDict:
				del valuesDict["memberDeviceList"]
			if "sourceDeviceMenu" in valuesDict:
				del valuesDict["sourceDeviceMenu"]
			return valuesDict

	####################
	# This is the method that's called to build the source device list. Note
	# that valuesDict is read-only so any changes you make to it will be discarded.
	####################
	def sourceDevices(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.debugLog("sourceDevices called with filter: %s  typeId: %s  targetId: %s" % (filter, typeId, str(targetId)))
		returnList = list()
		# if valuesDict doesn't exist yet - if this is a brand new device
		# then we just create an empty dict so the rest of the logic will
		# work correctly. Many other ways to skin that particular cat.
		if not valuesDict:
			valuesDict = {}
		# Get the member device id list, loop over all devices, and if the device
		# id isn't in the member list then include it in the source list.
		deviceList = valuesDict.get("memberDevices","").split(",")
		for devId in indigo.devices.iterkeys():
			if str(devId) not in deviceList:
				returnList.append((str(devId),indigo.devices.get(devId).name))
		return returnList

	####################
	# This is the method that's called to build the member device list. Note
	# that valuesDict is read-only so any changes you make to it will be discarded.
	####################
	def memberDevices(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.debugLog("memberDevices called with filter: %s  typeId: %s  targetId: %s" % (filter, typeId, str(targetId)))
		returnList = list()
		# valuesDict may be empty or None if it's a brand new device
		if valuesDict and "memberDevices" in valuesDict:
			# Get the list of devices
			deviceListString = valuesDict["memberDevices"]
			self.debugLog("memberDeviceString: " + deviceListString)
			deviceList = deviceListString.split(",")
			# Iterate over the list and if the device exists (it could have been
			# deleted) then add it to the list.
			for devId in deviceList:
				if int(devId) in indigo.devices:
					returnList.append((devId, indigo.devices[int(devId)].name))
		return returnList

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		# If the typeId is "scene", we want to clear the selections on both
		# dynamic lists so that they're not stored since we really don't
		# care about those.
		self.debugLog(u"validateDeviceConfigUi: typeId: %s  devId: %s" % (typeId, str(devId)))
		if typeId == "scene":
			if "memberDeviceList" in valuesDict:
				valuesDict["memberDeviceList"] = ""
			if "sourceDeviceMenu" in valuesDict:
				valuesDict["sourceDeviceMenu"] = ""
		return (True, valuesDict)

	########################################
	# Plugin Actions object callbacks (pluginAction is an Indigo plugin action instance)
	######################
	def resetHardware(self, pluginAction):
		self.debugLog("resetHardware action called:\n" + str(pluginAction))

	def updateHardwareFirmware(self, pluginAction):
		self.debugLog("updateHardwareFirmware action called:\n" + str(pluginAction))
