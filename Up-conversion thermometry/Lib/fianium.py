#	A python wrapper for Fianium supercontinuum laser coupled with AOTF controller

# 	Original code by Yurii Morozov
#   Adapted by Shubin Zhang

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.


import ctypes
import types
import time
import sys
import numpy as np
from time import sleep
d = ctypes.cdll.LoadLibrary('AotfLibrary.dll')
import atexit, string


class fianium_aotf():
	def __init__(self):
		self.aotf_serial_number = "***************"
		self.aotf_serial_number_2  = "*************"

		#Initialize aotf power as well as vis/nir channel id
		self.last_power = 0.
		self._id_ir = 0
		self._id_vis = 0

		self.vis_on = False
		self.ir_on = False

		#Parameters used to calculate RF frequency of aotf controller
		self.aotf_poly_coef_vis = [-6.82179219e-17,3.27832863e-13,-6.73661923e-10,7.68686873e-07,-5.27585574e-04, 2.18972280e-01, -5.14687930e+01, 5.48569847e+03]
		self.aotf_poly_coef_nir = [1.25692660e-17,-7.01326532e-14,1.65065114e-10,-2.11753075e-07,1.59015648e-04,-6.90936212e-02,1.55775592e+01,-1.19330653e+03]
		self.aotf_poly_vis = np.poly1d(self.aotf_poly_coef_vis)
		self.aotf_poly_nir = np.poly1d(self.aotf_poly_coef_nir)
		
		
		self.MAX_POWER = 5000   #Max ATOF power
		self.red_edge = 800.	#Max wavelength for visible channel
		atexit.register(self._close)

	def get_serial(self, prefix):
		strbuf = ctypes.c_char()
		bytesread = ctypes.c_uint()
		ser_cmd = "Boardid serial \r"
		d.AotfWrite(prefix, len(ser_cmd), ser_cmd)
		strbuf = ctypes.c_char()
		bytesread = ctypes.c_uint()
		ret = ''
		for i in range(0, 1000):
			time.sleep(0.002)	
			if d.AotfIsReadDataAvailable(prefix):
				val = d.AotfRead(prefix, ctypes.sizeof(strbuf), ctypes.byref(strbuf), ctypes.byref(bytesread))
				ret += strbuf.value
		print "sn ", ret
		return ret

	def _open(self):
		#Connect to AOTF controller
		self._id_vis = d.AotfOpen(0)
		ser1 = self.get_serial(self._id_vis)
		self._id_ir = d.AotfOpen(1)
		ser2 = self.get_serial(self._id_ir)
		if (self.aotf_serial_number in ser1) or (self.aotf_serial_number_2 in ser2):
			pass
		elif (self.aotf_serial_number in ser2) or (self.aotf_serial_number_2 in ser1):
			self._id_ir, self._id_vis = self._id_vis, self._id_ir
		else:
			raise ValueError('AOTF open failed: can not find device with serial number '+self.aotf_serial_number)
			return False	

	def _close(self):
		d.AotfClose(self._id_ir)
		d.AotfClose(self._id_vis)
		
	def send_cmd(self, cmd, prefix):
		strbuf = ctypes.c_char()
		bytesread = ctypes.c_uint()
		for i in range(100):
			sleep(0.000001)
			if d.AotfIsReadDataAvailable(prefix):
				ret = d.AotfRead(prefix, ctypes.sizeof(strbuf), ctypes.byref(strbuf), ctypes.byref(bytesread))
				
		d.AotfWrite(prefix, len(cmd), cmd)
		time.sleep(0.020)
		strbuf = ctypes.create_string_buffer(1)
		strbuf = ctypes.c_char()
		bytesread = ctypes.c_uint()
		ret = ''
		for i in range(100):
			sleep(0.000001)
			if d.AotfIsReadDataAvailable(prefix):
				ret = d.AotfRead(prefix, ctypes.sizeof(strbuf), ctypes.byref(strbuf), ctypes.byref(bytesread))
		return ret
		
	def enable(self):
		s = 'dau en\r dau gain 0 255\r'
		self.send_cmd(s, self._id_ir)
		self.send_cmd(s, self._id_vis)

	def set_wlen(self,wlen,aotf=None):
		#Set laser wavelength
		if "vis" in aotf:
			freq = self.aotf_poly_vis(wlen)
			s = 'dds freq 0 %0.3f \r' % (freq)
			self.send_cmd(s, self._id_vis)
			self.vis_on = True
		elif "nir" in aotf:
			freq = self.aotf_poly_nir(wlen)
			print "freq = ", freq
			s = 'dds freq 0 %0.3f \r' % (freq)
			self.send_cmd(s, self._id_ir)
			self.ir_on = True
			
	def set_pwr(self,power,aotf=None):
		#Set laser power
		self.last_power = power
		if "vis" in aotf:
			val = int(power*self.MAX_POWER/100.)
			s = 'dds amplitude 0 %d \r' % (val)
			self.send_cmd(s, self._id_vis)
		elif "nir" in aotf:
			val = int(power*self.MAX_POWER/100.)
			s = 'dds amplitude 0 %d \r' % (val)
			self.send_cmd(s, self._id_ir)		

		
			
if __name__ == '__main__':
	aotf = fianium_aotf()
	aotf._open()
	print "Aotf open"
	aotf.enable()
	print "Aotf enable"
	time.sleep(0.5)
	aotf.set_wlen(450, aotf="vis")
	print "Aotf vis set wavelength"
	aotf.set_pwr(100, aotf="vis")
	print "Aotf vis set power"
	aotf.set_wlen(700, aotf="nir")
	print "Aotf nir set wavelength"
	aotf.set_pwr(0, aotf="nir") 
	print "Aotf ir set power"



	
	
