#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Indigo interface to eversolar-monitor server
# Reads solar PV generation data from eversolar-monitor server directly connected to PV inverter
# eversolar-monitor available from http://code.google.com/p/eversolar-monitor/

# V1.0.1 17 January 2018 - repackaged for Indigo Plugin Library
# V1.0.0 4 June 2013 - first working version

import urllib2
import sys
import socket
import string
import simplejson as json


class EversolarMonitor(object):
    """Class to interface with the EversolarMonitor PV Inverter monitor service.

    Polls the EversolarMonitor service using the inverter-data resource, which returns
    a JSON formatted packet containing the current PV generation data from the inverter.
    
    Instance variables:
        plugin  	- represents the object containing an instance of this class.
        ipAddress 	- of the EversolarMonitor service
        ipPort		- of the EversolarMonitor service
        pollingFreq	- how frequently we call the service
        urlCmd		- constructed url of the service
        
    Constants:
        DEFAULT_PORT  - default port number used by eversolar-monitor.
        DATA_RESOURCE - resource used to retrieve inverter data
     
    """   

    # constants for EversolarMonitor
    DEFAULT_PORT = '3837'
    DATA_RESOURCE = 'inverter-data'

    ########################################    
    def __init__(self, plugin, ipAddress, ipPort, pollingFreq):
        """Store the reference to the containing object."""
        self.plugin = plugin
        self.ipAddress = ipAddress
        self.ipPort = ipPort
        self.pollingFreq = pollingFreq
        self.urlCmd = "http://" + ipAddress + ":" + ipPort + "/" + self.DATA_RESOURCE
        
        # setup a socket timeout
        timeout = 5
        socket.setdefaulttimeout(timeout)


    def getData(self, dev):
        """Get a JSON document from the eversolar-monitor server"""
        try:
            self.plugin.debugLog("getData called")
            req = urllib2.Request(self.urlCmd)
            opener = urllib2.build_opener()
            f = opener.open(req)
            return json.load(f)
                
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code

    def parsePacket(self, packet, dev):
        """Parse the JSON received"""
        self.plugin.debugLog("parsePacket called")
        self.walk(dev, packet)
                
    
    def walk(self, dev, node, parentKey="none"):
        """Recursively iterate over the JSON: call walk() on every Dict found
        Pass in the parent key in case we need to make a decision based on the
        context of the current key (e.g. handle duplicate keys). When we find a
        leaf node, update an Indigo state with the value, using the key as the
        name of the Indigo state """ 
        for key, item in node.items():
            if isinstance(item, dict):
                # what we've found is another dictionary, so recursively call walk again
                self.walk(dev, item, key)
            else:
                # annoyingly, two uses of the 'timestamp' key in different places in the JSON
                # use the parent key to decide which is which
                if (parentKey == "data" and key == "timestamp"):
                    key = "lastUpdated"
                dev.updateStateOnServer(key, item)
                self.plugin.debugLog("walk: updating %s with %s" % (key, item))
                	
    def listen(self, dev):
        """Get a JSON packet & then parse it"""
        packet = self.getData(dev)
        self.parsePacket(packet, dev)
    

            
