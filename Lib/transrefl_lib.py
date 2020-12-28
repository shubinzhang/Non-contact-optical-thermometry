#	A python wrapper for home built photo receiver and National Instrument 
#   multifunction I/O devices (4462 and 6229) to measure light intensity

# 	Original code by Yurii Morozov


#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.


from ctypes import *
from PyDAQmx import *
from PyDAQmx.DAQmxTypes import *
from time import sleep
import numpy as np
from numpy import append, linspace,zeros,mean
import atexit, string, ctypes
import time
measure_difference = False
dev_4462 = "Dev2"
dev_6229 = "Dev1"

class sia():
	def __init__(self, laserpulse=True):
		
		self.laserpulse = laserpulse
		self.set_default_device_config()
		self.set_default_wfrom()
		self.configure_devices(laserpulse=self.laserpulse)
		atexit.register(self.disconnect)

	def disconnect(self):
		try:
			DAQmxStopTask(self.taskHandleIn)
			DAQmxClearTask(self.taskHandleIn)
		
			DAQmxStopTask(self.taskHandleOut)
			DAQmxClearTask(self.taskHandleOut)
		except:
			"Print nothing to disconnect..."
	def ref_amp(self, max_int_time,laserpulse = False):
		if self.last_int_time>max_int_time:
			self.last_int_time = max_int_time
		self.set_int_time(self.last_int_time)
		int_time = self.last_int_time
		
		power_level = -1.
		self.ch1_level = 10.
		
		while (self.ch1_level>6.5 or self.ch1_level<1.)  and (int_time>=0.5 and int_time<=max_int_time):
			self.configure_devices(laserpulse=laserpulse)
			self.start_cycle()
			power_level = self.calc_amplitude(darksignal = False)
			
			if self.ch1_level>6.5:
				int_time = int_time/3.
				self.set_int_time(int_time)
			elif self.ch1_level<1.0:
				int_time = int_time*2.
				self.set_int_time(int_time)
			else:
				print " level is ok... "
				print "power_level = ", power_level
				print "self.ch1_level = ", self.ch1_level
				print "int_time = ", int_time
		return power_level
		
	def configure_devices(self, laserpulse=False):
		self.disconnect()
		
		self.power_coef1 = (3300.*10.**(-12))*self.samplerate_in*10.**(6) #current in uA, 100 pF = 10**(-10) F - capacitance in Farads 
		self.power_coef2 = (1000.*10.**(-12))*self.samplerate_in*10.**(6) #current in uA, 100 pF = 10**(-10) F - capacitance in Farads
		self.power_coef3 = (33.*10.**(-12))*self.samplerate_in*10.**(6) #current in uA, 100 pF = 10**(-10) F - capacitance in Farads
		
		if laserpulse:
			self.waveform = np.asarray(self.get_wfrom(self.samplerate_out,1), dtype=np.float64)
			self.N_samples_out = len(self.waveform)/4
		else:
			self.waveform = np.asarray(self.get_wfrom(self.samplerate_out,1, laserpulse=False), dtype=np.float64)
			self.N_samples_out = len(self.waveform)/3
		
		
		#period
		self.period = int(self.samplerate_in*(float(self.N_samples_out)/self.n_pulses)/float(self.samplerate_out))
		
		self.N_samples_in = int(self.samplerate_in*float(self.N_samples_out)/float(self.samplerate_out))+100 # +100???
		
		self.adc_array = np.zeros((self.N_samples_in*4), dtype=np.float64)
		
		self.n_of_obtained_samples = c_long()
		
		self.taskHandleIn = TaskHandle(0)
		self.taskHandleOut = TaskHandle(1)
		
		DAQmxCreateTask("", byref(self.taskHandleIn))
		DAQmxCreateTask("", byref(self.taskHandleOut))
		
		DAQmxCreateAIVoltageChan(self.taskHandleIn, "{0}/ai0, {0}/ai1, {0}/ai2 ".format(self.dev_4462), "", DAQmx_Val_Diff, float64(-10.), float64(0.3), DAQmx_Val_Volts, None)
		DAQmxSetAICoupling(self.taskHandleIn, "{0}/ai0, {0}/ai1, {0}/ai2".format(self.dev_4462), DAQmx_Val_DC)
		
		DAQmxCfgSampClkTiming(self.taskHandleIn, None, self.samplerate_in, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, self.N_samples_in)
		DAQmxSetStartTrigType(self.taskHandleIn,DAQmx_Val_DigEdge)
		DAQmxSetDigEdgeRefTrigEdge(self.taskHandleIn, DAQmx_Val_Rising)
		
		if laserpulse:
			DAQmxCreateAOVoltageChan(self.taskHandleOut, "{0}/ao0,{0}/ao1, {0}/ao2, {0}/ao3".format(self.dev_6229), "", float64(-1.0), float64(10.), DAQmx_Val_Volts, None)
			DAQmxCfgSampClkTiming(self.taskHandleOut, None, c_double(self.samplerate_out), DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, c_ulonglong(self.N_samples_out))
			DAQmxSetAOTermCfg(self.taskHandleOut, "{0}/ao0,{0}/ao1, {0}/ao2, {0}/ao3".format(self.dev_6229) ,DAQmx_Val_RSE)
		else:
			DAQmxCreateAOVoltageChan(self.taskHandleOut, "{0}/ao0,{0}/ao1, {0}/ao3".format(self.dev_6229), "", float64(-1.0), float64(10.), DAQmx_Val_Volts, None)
			DAQmxCfgSampClkTiming(self.taskHandleOut, None, c_double(self.samplerate_out), DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, c_ulonglong(self.N_samples_out))
			DAQmxSetAOTermCfg(self.taskHandleOut, "{0}/ao0,{0}/ao1, {0}/ao3".format(self.dev_6229) ,DAQmx_Val_RSE)
		#DAQmxCfgDigEdgeStartTrig(self.taskHandleOut, "/Dev2/ai/SampleClock", DAQmx_Val_Rising)
		
		self.n_of_obtained_samples = c_long()
		self.n_of_writed_samples = c_long()
		
		DAQmxWriteAnalogF64(self.taskHandleOut, c_long(self.N_samples_out), bool32(False), float64(1), DAQmx_Val_GroupByChannel, self.waveform,  byref(self.n_of_writed_samples), None)
	def start_cycle(self, show=False, discnct = False):
		
		# DAQmx Output Start Code
		DAQmxStartTask(self.taskHandleIn)
		#sleep(0.05)
		DAQmxStartTask(self.taskHandleOut)
		#/*/ DAQmx Input Start Code
		
		#/*/ DAQmx Input Read Code
		#DAQmxReadAnalogF64(taskHandleIn,sampsPerChanIn,10.0,DAQmx_Val_GroupByChannel,dataIn,sampsPerChanIn*numChannelsIn,&numRead,NULL
		DAQmxReadAnalogF64(self.taskHandleIn, self.N_samples_in,float64(self.time_out) , DAQmx_Val_GroupByChannel, self.adc_array, 3*self.N_samples_in, byref(self.n_of_obtained_samples), None)
		#/*/ DAQmx Output Wait Code
		DAQmxWaitUntilTaskDone(self.taskHandleOut,1.0)
		
		self.adc_0_array = self.adc_array[:self.n_of_obtained_samples.value]#-0.0055898
		self.adc_1_array = self.adc_array[self.n_of_obtained_samples.value:self.n_of_obtained_samples.value*2]#-0.0042831
		self.adc_2_array = self.adc_array[self.n_of_obtained_samples.value*2:self.n_of_obtained_samples.value*3]
		#self.adc_3_array = self.adc_array[self.n_of_obtained_samples.value*3:self.n_of_obtained_samples.value*4]
		
		DAQmxStopTask(self.taskHandleIn)
		DAQmxStopTask(self.taskHandleOut)
	
	#def __calc_tr(self,dark=False):
		
	def calc_amplitude(self, darksignal=True):
		period  = self.period 		
		
		xs = np.arange(self.t2_laser-self.t1_laser)
		xb = np.arange(self.t2_dark-self.t1_dark)
		xs = xs[:-1]
		xb = xb[:-1]
		
		#A = np.vstack([xs, np.ones(len(xs))]).T
		#Ad = np.vstack([xb, np.ones(len(xb))]).T
		
		x = self.adc_0_array 
		y = self.adc_1_array 
		z = self.adc_2_array
		
		
		
		xf = x[self.t1_laser:self.t2_laser]
		yf = y[self.t1_laser:self.t2_laser]
		zf = z[self.t1_laser:self.t2_laser]
		
		xf_drk = x[self.t1_dark:self.t2_dark]
		yf_drk = y[self.t1_dark:self.t2_dark]
		zf_drk = z[self.t1_dark:self.t2_dark]
		
		"""	
		kx, bx = np.linalg.lstsq(A, xf[0:-1])[0]
		ky, by = np.linalg.lstsq(A, yf[0:-1])[0]
		kz, bz = np.linalg.lstsq(A, zf[0:-1])[0]
	
		kyd = 0.
		kxd = 0.
		kzd = 0.
		"""
		
		xf = np.diff(xf)
		yf = np.diff(yf)
		zf = np.diff(zf)
		
		xf_drk = np.diff(xf_drk)
		yf_drk = np.diff(yf_drk)
		zf_drk = np.diff(zf_drk)
			
		if darksignal:	
			X_amp = (np.mean(xf)-np.mean(xf_drk))#*len(xf)
			Y_amp = (np.mean(yf)-np.mean(yf_drk))#*len(yf)
			Z_amp = (np.mean(zf)-np.mean(zf_drk))#*len(zf)
		else:
			X_amp = 0.5*(np.mean(xf)+np.mean(xf_drk))#*len(xf)
			Y_amp = 0.5*(np.mean(yf)+np.mean(yf_drk))#*len(yf)
			Z_amp = 0.5*(np.mean(zf)+np.mean(zf_drk))#*len(zf)
		
		
		
		self.ch1_level = -X_amp*len(xf)
		self.ch2_level = -Y_amp*len(yf)
		self.ch3_level = -Z_amp*len(zf)
		
		self.ch1_amp = -X_amp*self.power_coef1 #3300 pF
		self.ch2_amp = -Y_amp*self.power_coef2 #1000 pF #looks like smth wrong with this value, maybe
		self.ch3_amp = -Z_amp*self.power_coef3 #33 pF #looks like smth wrong with this value, maybe
		
		
		return self.ch1_amp
	
	def calc_amplitudes(self, darksignal=True):
		period  = self.period 		
		
		xs = np.arange(self.t2_laser-self.t1_laser)
		xb = np.arange(self.t2_dark-self.t1_dark)
		xs = xs[:-1]
		xb = xb[:-1]
		
		#A = np.vstack([xs, np.ones(len(xs))]).T
		#Ad = np.vstack([xb, np.ones(len(xb))]).T
		
		x = self.adc_0_array 
		y = self.adc_1_array 
		z = self.adc_2_array
		
		
		
		xf = x[self.t1_laser:self.t2_laser]
		yf = y[self.t1_laser:self.t2_laser]
		zf = z[self.t1_laser:self.t2_laser]
		
		xf_drk = x[self.t1_dark:self.t2_dark]
		yf_drk = y[self.t1_dark:self.t2_dark]
		zf_drk = z[self.t1_dark:self.t2_dark]
		
		"""	
		kx, bx = np.linalg.lstsq(A, xf[0:-1])[0]
		ky, by = np.linalg.lstsq(A, yf[0:-1])[0]
		kz, bz = np.linalg.lstsq(A, zf[0:-1])[0]
	
		kyd = 0.
		kxd = 0.
		kzd = 0.
		"""
		
		xf = np.diff(xf)
		yf = np.diff(yf)
		zf = np.diff(zf)
		
		xf_drk = np.diff(xf_drk)
		yf_drk = np.diff(yf_drk)
		zf_drk = np.diff(zf_drk)
			
		if darksignal:	
			X_amp = (np.mean(xf)-np.mean(xf_drk))#*len(xf)
			Y_amp = (np.mean(yf)-np.mean(yf_drk))#*len(yf)
			Z_amp = (np.mean(zf)-np.mean(zf_drk))#*len(zf)
		else:
			X_amp = 0.5*(np.mean(xf)+np.mean(xf_drk))#*len(xf)
			Y_amp = 0.5*(np.mean(yf)+np.mean(yf_drk))#*len(yf)
			Z_amp = 0.5*(np.mean(zf)+np.mean(zf_drk))#*len(zf)
		
		
		
		self.ch1_level = -X_amp*len(xf)
		
		self.ch1_amp = -X_amp*self.power_coef1 #3300 pF
		self.ch2_amp = -Y_amp*self.power_coef2 #1000 pF #looks like smth wrong with this value, maybe
		self.ch3_amp = -Z_amp*self.power_coef3 #33 pF #looks like smth wrong with this value, maybe
		
		
		return self.ch1_amp, self.ch2_amp, self.ch3_amp
		
	def calc_ratios(self, N, darksignal=True):
		period  = self.period 
		N = self.n_pulses
		X_amp = zeros((N))
		Y_amp = zeros((N))
		Z_amp = zeros((N))
		
		xs = np.arange(self.t2_laser-self.t1_laser)
		xb = np.arange(self.t2_dark-self.t1_dark)
		xs = xs[:-1]
		xb = xb[:-1]
		
		A = np.vstack([xs, np.ones(len(xs))]).T
		Ad = np.vstack([xb, np.ones(len(xb))]).T
		
		x = self.adc_0_array 
		y = self.adc_1_array 
		z = self.adc_2_array
		
		sgn_tmp = zeros((0))
		sgn_fit_tmp = zeros((0))
		sgn_fit_csd_tmp = zeros((0))
		sgn_tmp_b = zeros((0))
		
		refl_fit_csd_tmp = zeros((0))
		reflar2 = zeros((0))
		
		for i in range(N):
			#y_zero = mean(y[period*i+580:period*i+620])
			#x_zero = mean(x[period*i+580:period*i+620])
			
			#y_int = mean(y[period*i+892:period*i+920])
			#x_int = mean(x[period*i+892:period*i+920])
			
			#y_zero_b = mean(y[period*i+190:period*i+220])
			#x_zero_b = mean(x[period*i+190:period*i+220])
			
			#y_int_b = mean(y[period*i+480:period*i+520])
			#x_int_b = mean(x[period*i+480:period*i+520])
		
			
			
			#x_amp_cur = x_int - x_zero
			#y_amp_cur = y_int - y_zero
			
			#x_amp_cur_b = x_int_b - x_zero_b
			#y_amp_cur_b = y_int_b - y_zero_b
			
			#sgn_tmp_b = append(sgn_tmp_b,(y_amp_cur-y_amp_cur_b)/(x_amp_cur-x_amp_cur_b))
			#sgn_tmp = append(sgn_tmp,y_amp_cur/x_amp_cur)
		
			xf = x[period*i+self.t1_laser:period*i+self.t2_laser]
			yf = y[period*i+self.t1_laser:period*i+self.t2_laser]
			zf = z[period*i+self.t1_laser:period*i+self.t2_laser]
			
			xf_drk = x[period*i+self.t1_dark:period*i+self.t2_dark]
			yf_drk = y[period*i+self.t1_dark:period*i+self.t2_dark]
			zf_drk = z[period*i+self.t1_dark:period*i+self.t2_dark]
			"""
			kx, bx = np.linalg.lstsq(A, xf[0:-1])[0]
			ky, by = np.linalg.lstsq(A, yf[0:-1])[0]
			kz, bz = np.linalg.lstsq(A, zf[0:-1])[0]
			"""			
			xf = np.diff(xf)
			yf = np.diff(yf)
			zf = np.diff(zf)
			if darksignal:
				xf_drk = np.diff(xf_drk)
				yf_drk = np.diff(yf_drk)
				zf_drk = np.diff(zf_drk)
			else:
				xf_drk = 0.
				yf_drk = 0.
				zf_drk = 0.
			"""
			AL = np.vstack([yf, np.ones(len(yf))]).T
			
			knn, bnn = np.linalg.lstsq(AL, xf)[0]
			
			self.knn, self.bnn = knn, bnn
			"""
			
			
			self.xf = xf
			self.yf = yf
			#self.kx, self.bx = kx, bx
			#self.ky, self.by = ky, by
			###
	##		xfd = x[period*i+self.t1_dark:period*i+self.t2_dark]
	##		yfd = y[period*i+self.t1_dark:period*i+self.t2_dark]
			zfd = z[period*i+self.t1_dark:period*i+self.t2_dark]
			
	##		kxd, bxd = np.linalg.lstsq(Ad, xfd)[0]
	##		kyd, byd = np.linalg.lstsq(Ad, yfd)[0]
	#		kzd, bzd = np.linalg.lstsq(Ad, zfd)[0]
			###
			kyd = 0.
			kxd = 0.
			kzd = 0.
			#sgn_fit_tmp = append(sgn_fit_tmp,((ky)/(kx)))
		##	sgn_fit_csd_tmp = append(sgn_fit_csd_tmp,(ky-kyd)/(kx-kxd))
			#sgn_fit_csd_tmp = append(sgn_fit_csd_tmp,np.mean(xf/yf))
			sgn_fit_csd_tmp = append(sgn_fit_csd_tmp,(np.mean(yf)-np.mean(yf_drk))/(np.mean(xf)-np.mean(xf_drk))) #11.3.2014 used to be append(sgn_fit_csd_tmp,np.mean(xf)/np.mean(yf))
			refl_fit_csd_tmp = append(refl_fit_csd_tmp,(np.mean(zf)-np.mean(zf_drk))/(np.mean(xf)-np.mean(xf_drk)))
			
	##15 Jan 2015		refl_fit_csd_tmp = append(refl_fit_csd_tmp, (kz-kzd)/(kx-kxd))
	#		reflar2 = append(reflar2, (kz-kzd)/(kx-kxd))
			
			#X_amp[i] = (kx-kxd)*len(xf)
			#X_amp[i] = (kx-kxd)*len(xf)
			
			#Y_amp[i] = (ky-kyd)*len(yf)
			#Z_amp[i] = (kz-kzd)*len(zf)
			X_amp[i] = (np.mean(xf)-np.mean(xf_drk))#*len(xf)
			Y_amp[i] = (np.mean(yf)-np.mean(yf_drk))#*len(yf)
			Z_amp[i] = (np.mean(zf)-np.mean(zf_drk))#*len(zf)
		self.ch1_amp = -mean(X_amp)*self.power_coef1
		self.ch2_amp = -mean(Y_amp)*self.power_coef2 #looks like smth wrong with this value
		self.ch3_amp = -mean(Z_amp)*self.power_coef3 #looks like smth wrong with this value
			
		#self.signal_cur = mean(sgn_tmp)
		#self.signal_cur_csd = mean(sgn_tmp_b)
		#self.sgn_fit = mean(sgn_fit_tmp)
		self.reference = self.ch1_amp
		self.trans = mean(sgn_fit_csd_tmp)
		self.refl = mean(refl_fit_csd_tmp)
		self.refl2 = self.refl#mean(reflar2)
	
	def set_int_time(self, inttime):
		#integration time in ms
		self.int_time = inttime
		self.last_int_time = self.int_time
		self.configure_devices()
			
	def set_default_device_config(self):
		self.dev_4462 = "Dev2"
		self.dev_6229 = "Dev1"
		
		self.time_out = 20.0
		self.samplerate_in = 200000
		self.samplerate_out = 80000
		self.N_samples_in = 2048
		
	def set_device_config(self, dev_config_dict):
		self.dev_4462 = dev_config_dict['dev_4462']
		self.dev_6229 = dev_config_dict['dev_6229']
		self.samplerate_in = dev_config_dict['samplerate_in']
		self.samplerate_out = dev_config_dict['samplerate_out']
		
		#self.time_out = dev_config_dict['time_out']
		
	def set_default_wfrom(self):
		
		self.sync_ofst = 0.05 #mS time between sync pulse front edge and hold pulse
		self.sync_time = 0.2 #mS duration of the sync pulse 
		self.sync_pulse_level = 4.5 #V
		
		self.int_time = 3.2 # mS
		self.last_int_time = self.int_time
		
		self.laser_delay = 0.05 # mS
		self.ofst_time = 0.05 #mS
		self.dead_time = 0.05 #mS
		self.rst_time = 0.05 # mS
		self.hld_time = 0.8 #mS
		self.high_lvl = 4.0
		self.low_lvl = 0.0
		self.laser_high_lvl = 5.
		self.laser_low_lvl = 0.
		###
		self.delta = 0.05 # mS
	def set_wfrom(self,settings_dict):
		self.settings_dict = settings_dict
		print self.settings_dict
		self.sync_ofst = self.settings_dict['sync_ofst']
		self.sync_time = self.settings_dict['sync_time']
		self.sync_pulse_level = self.settings_dict['sync_pulse_level']
		
		self.int_time = self.settings_dict['int_time']
		self.laser_delay = self.settings_dict['laser_delay']
		self.ofst_time = self.settings_dict['ofst_time'] 
		self.dead_time = self.settings_dict['dead_time']
		self.rst_time = self.settings_dict['rst_time']
		self.hld_time = self.settings_dict['hld_time']
		self.high_lvl = self.settings_dict['high_lvl'] 
		self.low_lvl = self.settings_dict['low_lvl']
		self.laser_high_lvl = self.settings_dict['laser_high_lvl']
		self.laser_low_lvl = self.settings_dict['laser_low_lvl']
		###
		self.delta = self.settings_dict['delta']
	def get_wfrom(self,srate, n_pulses, laserpulse = False):
		#srate = 80000
		self.n_pulses = n_pulses
		t1_laser_ms = 0.37+self.hld_time+self.laser_delay+self.delta
		t2_laser_ms = t1_laser_ms+self.int_time-self.laser_delay-3*self.delta
		
		self.t1_laser = int(self.samplerate_in*t1_laser_ms/1000.)
		self.t2_laser = int(self.samplerate_in*t2_laser_ms/1000.)
		
		self.t1_dark = int(self.samplerate_in*(t1_laser_ms+self.hld_time+self.int_time)/1000.)
		self.t2_dark = int(self.samplerate_in*(t2_laser_ms+self.hld_time+self.int_time)/1000.)
		
		#print "self.t1_laser, self.t2_laser",self.t1_laser, self.t2_laser
		#print "self.t1_dark, self.t2_dark",self.t1_dark, self.t2_dark
		#reset
		rst_pls = self.low_lvl*np.ones((int(srate*(self.ofst_time+(self.hld_time-self.rst_time)/2.)/1000.)))
		rst_pls = np.append(rst_pls, np.zeros((int(srate*self.rst_time/1000.))))
		
		rst_pls = np.append(rst_pls, self.high_lvl*np.ones((int(srate*(self.int_time+self.hld_time-self.rst_time)/1000.))))
		
		rst_pls = np.append(rst_pls, np.zeros((int(srate*self.rst_time/1000.))))
		
		rst_pls = np.append(rst_pls, self.high_lvl*np.ones((int(srate*(self.int_time+self.hld_time-self.rst_time)/1000.))))
		
		rst_pls = np.append(rst_pls, np.zeros((int(srate*self.rst_time/1000.))))
		
		rst_pls = np.append(rst_pls,self.low_lvl*np.ones((-2+int(srate*(self.dead_time+(self.hld_time-self.rst_time)/2.)/1000.))))
		rst_pls = np.append(rst_pls, np.zeros((2)))
		
		#hold
		hld_pls = self.low_lvl*np.ones((int(srate*self.ofst_time/1000.)))
		hld_pls = np.append(hld_pls, self.high_lvl*np.ones((int(srate*self.hld_time/1000.))))
	
		hld_pls = np.append(hld_pls, self.low_lvl*np.ones((int(srate*self.int_time/1000.))))
	
		hld_pls = np.append(hld_pls, self.high_lvl*np.ones((int(srate*self.hld_time/1000.))))
		
		hld_pls = np.append(hld_pls, self.low_lvl*np.ones((int(srate*self.int_time/1000.))))
		
		hld_pls = np.append(hld_pls, self.high_lvl*np.ones((int(srate*self.hld_time/1000.))))
		
		hld_pls = np.append(hld_pls, self.low_lvl*np.ones((int(srate*self.dead_time/1000.))))
		
		#laser
		laser_pls = self.laser_low_lvl*np.ones((int(srate*(self.ofst_time+self.hld_time+self.laser_delay)/1000.)))
		
		laser_pls = np.append(laser_pls, self.laser_high_lvl*np.ones((int(srate*self.int_time+2*self.laser_delay)/1000.)))
		#laser_pls = np.append(laser_pls, self.laser_high_lvl*np.ones((int(srate*self.int_time-2*self.laser_delay)/1000.)))
		#laser_pls = np.append(laser_pls, self.laser_high_lvl*np.ones((int(srate*(self.int_time+2*self.laser_delay)/1000.))))
		laser_pls = np.append(laser_pls, self.laser_low_lvl*np.ones((int(srate*self.dead_time+2*self.hld_time+self.int_time+self.laser_delay)/1000.)))
		
		#sync pulse
		sync_pulse = np.zeros((int(srate*(self.ofst_time-self.sync_ofst)/1000.)))
		sync_pulse = np.append(sync_pulse, self.sync_pulse_level*np.ones((int(srate*self.sync_time/1000.))))
		sync_pulse = np.append(sync_pulse, np.zeros((len(hld_pls)-len(sync_pulse))) )
		
		#plt.show()
		rst_pulse = np.tile(rst_pls,n_pulses)
		waveform = rst_pulse
		
		waveform = np.append(waveform, np.tile(hld_pls,n_pulses))
		#waveform = np.append(waveform, hld_pls)
		
		if laserpulse:
			waveform = np.append(waveform, np.tile(laser_pls,n_pulses))		
			#waveform = np.append(waveform,np.ones(len(laser_pls))*laser_low_lvl)
		
		waveform = np.append(waveform,sync_pulse)
		waveform = np.append(waveform,np.zeros(len(rst_pulse)-len(sync_pulse)))
		#waveform = rst_pulse, hld_pls, laser_pls, sync_pulse
		return waveform
