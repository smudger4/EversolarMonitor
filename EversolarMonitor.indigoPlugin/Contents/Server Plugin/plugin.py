#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Add an interface to eversolar-monitor to Indigo
# Reads solar PV generation data from eversolar-monitor server directly connected to PV inverter
# eversolar-monitor available from http://code.google.com/p/eversolar-monitor/
#
# Uses example code from Indigo SDK v1.02
# Copyright (c) 2012, Perceptive Automation, LLC. All rights reserved.
# http://www.perceptiveautomation.com
#
# V1.0.1 17 January 2018 - repackaged for Indigo Plugin Library
# V1.0.0 4 June 2013 - first working version

import os
import sys
import struct

from eversolarMonitor import EversolarMonitor

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.


################################################################################
class Plugin(indigo.PluginBase):
    """Indigo Plugin class, adding EversolarMonitor support to Indigo.
    
    Class variables:
        deviceDict      - dictionary of DeviceID / Device tuples
        
    """
    deviceDict = {}

    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.deviceList = []

    def __del__(self):
        indigo.PluginBase.__del__(self)

    ########################################
    def startup(self):
        self.debugLog(u"startup called")

    def shutdown(self):                     # called after runConcurrentThread() exits
        self.debugLog(u"shutdown called")
        
    ########################################
    def deviceStartComm(self, dev):
        """Initialise Indigo device & reset all server states."""
        self.debugLog("Starting device: " + dev.name)
        
        # force re-read of device states from Devices.xml
        dev.stateListOrDisplayStateIdChanged()
        
        # stash device ID
        if dev.id not in self.deviceList:
            self.deviceList.append(dev.id)
        if dev.id not in self.deviceDict:
            self.deviceDict[dev.id] = dev
                        
        # reset device states
        dev.updateStateOnServer("connected", '0')
        dev.updateStateOnServer("serial", '0')
        dev.updateStateOnServer("id_string", '0')
        dev.updateStateOnServer("timestamp", '0')
        dev.updateStateOnServer("watts", '0')
        dev.updateStateOnServer("e_today", '0')
        dev.updateStateOnServer("e_total", '0')
        dev.updateStateOnServer("iac", '0')
        dev.updateStateOnServer("op_mode", '0')
        dev.updateStateOnServer("frequency", '0')
        dev.updateStateOnServer("vac", '0')
        dev.updateStateOnServer("hours_up", '0')
        dev.updateStateOnServer("temp", '0')
        dev.updateStateOnServer("vpv", '0')
        dev.updateStateOnServer("ipv", '0')
        dev.updateStateOnServer("pac", '0')
        dev.updateStateOnServer("response_timeout_count", 0)
        dev.updateStateOnServer("lastUpdated", '0')
        dev.updateStateOnServer("ipv2", '0')
        dev.updateStateOnServer("vpv2", '0')
        dev.updateStateOnServer("impedance", '0')       # yes, it's spelt incorrectly... :-)
        dev.updateStateOnServer("total_daykwh", '0')
        dev.updateStateOnServer("total_power", '0')

            
    ########################################
    def deviceStopComm(self, dev):
        """Device stopping so clean up & remove stored references to it."""
        self.debugLog("Stopping device: " + dev.name)
                
        if dev.id in self.deviceList:
            self.deviceList.remove(dev.id)
        if dev.id in self.deviceDict:
            del self.deviceDict[dev.id]

    
    ########################################
    def runConcurrentThread(self):
        """Start the EversolarMonitor handler instance.
        
        A new thread is automatically created and runConcurrentThread() is called
        in that thread after startup() has been called. 
    
        runConcurrentThread() should loop forever and only return after self.stopThread
        becomes True. If this function returns prematurely then the plugin host process
        will log an error and attempt to call runConcurrentThread() again after several seconds.
                
        """
        self.debugLog(u"runConncurrentThread called")
        
        for deviceId in self.deviceList: 
            # get device instance & associated IP address
            dev = indigo.devices[deviceId]
            
            # read properties & create EversolarMonitor object
            self.ipAddr = dev.pluginProps["ipAddress"]
            self.ipPort = dev.pluginProps["ipPort"]
            self.pollFreq = dev.pluginProps["pollFreq"]
            self.monitor = EversolarMonitor(self, self.ipAddr, self.ipPort, self.pollFreq)

        try:            
            while self.stopThread != True:                       
                for deviceId in self.deviceList: 
                    # get device instance & associated IP address
                    thisDevice = indigo.devices[deviceId]
                    self.monitor.listen(thisDevice)
                    
                    # store key data items in Indigo variable for ease of reuse
                    gen = thisDevice.states['pac']
                    volts = thisDevice.states['vac']
                    genToday = thisDevice.states['e_today']
                    maxToday = thisDevice.states['watts']
                    self.updateVariable("EM_Power_Gen", str(gen))
                    self.updateVariable("EM_Volts", str(volts))
                    self.updateVariable("EM_Power_Gen_Today", str(int(float(genToday)*1000)))	# convert to Watts from KW
                    self.updateVariable("EM_Power_Gen_Max_Today", str(maxToday))
                    
                    # write log entries
                    self.serverLog("Inverter_watts=%s" % gen)
                    self.serverLog("Inverter_volts=%s" % volts)
                
                self.debugLog("runConcurrentThread: sleeping...")    
                self.sleep(int(self.pollFreq))
                               
        except self.StopThread:
            pass    # Optionally catch the StopThread exception and do any needed cleanup.

    ########################################
    def stopConcurrentThread(self):
        """Stop the EversolarMonitor handler instance.
        
        """ 
        indigo.PluginBase.stopConcurrentThread(self)
 
    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        """Validate details  provided by user - at present only checks polling freq."""
        pollFreq = int(valuesDict["pollFreq"])
        if (pollFreq <= 0 and pollFreq >= 300):
            self.errorLog(u"Error: polling frequency \"%s\" must be between 0 & 300 seconds" % pollFreq)
            errorDict = indigo.Dict()
            errorDict["address"] = "The value of this field must be between 0 & 300 seconds"
            return (False, valuesDict, errorDict)
        else:
            return True
                
    ########################################
    # wrap Indigo convenience functions so can be substituted in test harness
        
    def serverLog(self, text):
        indigo.server.log(text)
        
    def updateVariable(self, varName, varVal):
        """Update value of Indigo variable & if it doesn't exist, create it"""
        try:
            myVar = indigo.variables[varName]
            indigo.variable.updateValue(myVar, varVal)
        except KeyError, e:
            indigo.server.log("Created variable '%s' with value '%s'" % (varName, varVal))
            myVar = indigo.variable.create(varName, varVal)
 