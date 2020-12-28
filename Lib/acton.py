#	Acton - A python wrapper for Acton SP-2300i spectrometer coupled with CCD camera

# 	Original code by Yurii Morozov

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

import serial
import atexit, string
import time
class Acton():
	"""
	acton sp-2300i
	1 - Mirror
	2 - 1200 gr/mm 500 nm blaze
	3 - 150 gr/mm 800 nm blaze
	"""
	def __init__(self,com=*, grating=2):
		
		#Parameters to correlate ccd camera pixel horizontal position with wavelength
		self.zero_position = 308 

		#Parameters for grating 3 - 150 gr/mm 800 nm blaze
		self.k_calibr_3 = -0.3389 
		self.b_calibr_3 = 546.1 - 441.84

		#Parameters for grating 2 - 1200 gr/mm 500 nm blaze
		self.k_calibr_2 = -0.0319 
		self.b_calibr_2 =  785 - 773.84  

		self.delta_wlen = 1.  #Grating center wavlength tolerance
		self.last_wlen = -1	  #Previous grating center wavlength
		
		#Connect spectrometer through usb port using pyserial. More information can be found in https://pypi.org/project/pyserial/
		self.port_is_open = False
		self.grating = grating
		self.baud_rate = 9600
		self.port = '\\\\.\\COM'+str(com)
		self.ser = serial.Serial()
		self.ser.baudrate = self.baud_rate
		self.ser.port = self.port
		self.ser.timeout = 5.
		if self.ser.isOpen():
			self.ser.close()
			time.sleep(0.3)
		else:
			try:
				print "trying to open port ", com
				self.ser.open()
			except serial.SerialException:
				print "port is already open..."	
		if self.ser.isOpen():
			self.port_is_open = True
		self.ser.flushInput()
		
		self.ser.write("?GRATINGS \r")
		print self.waitreply()
		print "Current wavelength = ", self.get_wavelength()
		print "Current grating = ", self.get_grating()
		self.check_grating()
		atexit.register(self.close)

	def check_grating(self, ask=True):
		self.grating = self.get_grating()
		print "Grating  = ", self.grating
		if self.grating==3:
			self.k_calibr = self.k_calibr_3
			self.b_calibr = self.b_calibr_3
		elif self.grating==2:
			self.k_calibr = self.k_calibr_2
			self.b_calibr = self.b_calibr_2
				
	def get_wavelength(self):
		self.ser.write("?NM\r")
		reply = self.waitreply()
		self.last_wlen = float(str(reply.split()[0]))
		return self.last_wlen
	
	def change_grating(self,grating):
		self.ser.write(str(int(grating))+" GRATING"+"\r") 
		reply = self.waitreply()
		self.check_grating()
		print reply
				
	def get_grating(self):
		self.ser.write('?GRATING \r')
		reply = self.waitreply()
		self.grating = int(reply.strip().split()[0])
		return self.grating
	
	def get_slit(self):
		print "Slit is not motorized in Acton spectrometer!"
		return True
	def set_slit(self, slit):
		print "Slit is not motorized in Acton spectrometer!"
		return True
		  
	def waitreply(self, timeout=20):
		responce = ""
		time1 = time.time()
		elapsedtime = 0
		while not("ok" in responce):
			response = response+self.ser.read(10)
			time.sleep(0.005)
			elapsedtime = time.time()-time1
			if elapsedtime > timeout:
				print "Timeout error!"
				return False
		return response

	def set_wavelength(self, wlen, cw=False):
		"""
		cw means spectrometer will be set to specific wavelength in the middle of CCD chip, (row number 256)
		it will use calibration constants self.k_calibr and self.b_calibr to move to specific wavelength
		check if we need to move spectrometer
		"""
		print "self.last_wlen, wlen"
		print self.last_wlen, wlen
		if abs(self.last_wlen-wlen) < self.delta_wlen:
			return self.last_wlen

		wlen = int(wlen - self.zero_position*self.k_calibr - self.b_calibr)
		self.ser.write('%1.2f GOTO\r'%wlen)
		self.cur_wlen = self.get_wavelength()
		return self.last_wlen

	
	def close(self):
		if self.port_is_open:
			self.ser.close()
		else:
			print "Device connected to port ", str(self.ser.port), " is already closed..."
