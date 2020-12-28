#	A python wrapper for Newport electronic fast shutter controlled by National Instrument multifunction I/O device as well as home built pulse singal generator.
#   This library is based on PyDAQmx, more informatio about PyDAQmx functions can be found in https://zone.ni.com/reference/en-XX/help/370471AM-01/
 	
#   Original code by Yurii Morozov
#   Adapted by Shubin Zhang

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.



import os
if os.environ['USCAN_PYQT_VERSION']=='5':
	from PyQt5 import QtCore, QtGui
elif os.environ['USCAN_PYQT_VERSION']=='4':
	from PyQt4 import QtCore, QtGui
from ctypes import *
from PyDAQmx import *
from PyDAQmx.DAQmxTypes import *
from time import sleep
import numpy as np

class start_digital_io():
	def __init__(self, port, line):
		#Connect National Instrument and initialize parameters, 8-bits port is used. 
		self.prev_state = False
		self.dev_id = "Dev1"
		self.time_out = 0.01
		self.port_nmbr = port  
		self.line_nmbr = line
		self.configure()
		
			
	def disconnect(self):
		try:
			DAQmxStopTask(self.taskHandle)
			DAQmxClearTask(self.taskHandle)
		except:
			print "nothing to disconnect..."


	def configure(self):
		self.disconnect()
		self.taskHandle = TaskHandle(0)
		DAQmxCreateTask("", byref(self.taskHandle))
		DAQmxCreateDOChan(self.taskHandle,"{0}/port{1}/line0:7".format(self.dev_id, str(int(self.port_nmbr))),"",DAQmx_Val_ChanForAllLines)
		DAQmxStartTask(self.taskHandle)
		data = [0,0,0,0,0,0,0,0] #
		data = np.asarray(data, dtype=np.uint8)
		DAQmxWriteDigitalLines(self.taskHandle,int32(1),bool32(True),float64(self.time_out),DAQmx_Val_GroupByChannel,data,None,None)
		
	def onoff(self):
		data = [0,0,0,0,0,0,0,0]
		data[self.line_nmbr] = not(self.prev_state) 
		self.prev_state = not(self.prev_state)
		print "On/Off"
		print "current status", self.prev_state
		data = np.asarray(data, dtype=np.uint8)
		DAQmxWriteDigitalLines(self.taskHandle,int32(1),bool32(True),float64(self.time_out),DAQmx_Val_GroupByChannel,data,None,None)

		
	def seton(self, delay=True): #open shutter
		self.prev_state = True
		self.onoff()
		if delay: sleep(0.15)

	def setoff(self, delay=True): #close shutter
		self.prev_state = False
		self.onoff()
		if delay: sleep(0.15)
		

