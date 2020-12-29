'''
Instrument control program for up-conversion thermometry, more information can
be found in following link https://www.sciencedirect.com/science/article/abs/pii/S0022231319322847?via%3Dihub

Original code by
Copyright (C) 2018  Shubin Zhang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation
'''


from time import sleep
import time
import sys
import os
from Lib import acton
from Lib import fianium
from Lib import transrefl_lib
from Lib import andor_camera
from filterwhl import fw102c
from digitalio import digitalio
from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from datetime import datetime as dt
import matplotlib.pyplot as plt
from config import setting_dict_upconversion as setting_dict

class Stokes_AS():
    ###Connect instruments
    def __init__(self,setting_dict):
        self.cur_time = dt.now()
        self.app = QtGui.QApplication(sys.argv)
        self.camera = andor_camera.AndorCamera() #connect ccd camera
        self.camera_cooldown()
        self.camera_setting(setting_dict)
        self.acton = acton.Acton(com = setting_dict["acton_port"], grating = 3) #connect spectrometer
        self.fianium = fianium_py.fianium_aotf() #connect laser
        self.sia =transrefl_lib.sia()            #connect photo receiver for reference
        self.fw = fw102c.FW102C(port = setting_dict["filter_wheel"])  #connect filter wheel
        self.get_aqu_setting(setting_dict)
        self.fianium.enable()                    
        self.dio = digitalio.start_digital_io(setting_dict["shutter_port"], setting_dict["shutter_line"])   #connect shutter
        self.dspl = setting_dict["dspl"]
        self.save = setting_dict["save"]
        if self.dspl:   #Show PL/ASPL spctrum as well as integrated intensity
            self.ploto1 = pg.plot()
            self.ploto2 = pg.plot()
            self.ploto3 = pg.plot()
            self.ploto1.showGrid(x=True, y=True, alpha=1.)
            self.ploto2.showGrid(x=True, y=True, alpha=1.)
            self.ploto3.showGrid(x=True, y=True, alpha=1.)
            self.stokes_spectra_curve = self.ploto1.plot(pen = pg.mkPen('r', width=1.5))
            self.as_spectra_curve = self.ploto2.plot(pen = pg.mkPen('b', width=1.5))
            self.stokes_sum_curve = self.ploto3.plot(pen = pg.mkPen('r', width=1.5))
            self.as_sum_curve = self.ploto3.plot(pen = pg.mkPen('b', width=1.5))

    def get_aqu_setting(self,dict):
        self.wlen_start = float(dict["wlen_start"])
        self.slit = 20  #default value
        self.N_scans = int(dict["N_scans"]) 
        self.N_wl_change = int(dict["N_wl_change"])
        self.fianium_stokes_wl = int(dict["wl1"])
        self.fianium_as_wl = int(dict["wl2"]) 
        self.fianium_stokes_power = int(dict["power1"])
        self.fianium_as_power = int(dict["power2"])

    #Cooling down CCD camera
    def camera_cooldown(self):
        self.camera.SetCoolerMode(1)
        self.camera.CoolerON()
        self.camera.SetTemperature(-80) 
        self.camera.GetTemperature()
        cur_T = float(self.camera._temperature)
        print "current camera temperature",cur_T
        while  cur_T > -70:
            self.camera.GetTemperature()
            time.sleep(0.1)
            cur_T = float(self.camera._temperature)
            print "current Temperature is ", cur_T
            print "current status ", self.camera.GetTemperature()
            time.sleep(10)
        print "Temperature is stable now"
    
    
    #Set up camera
    def camera_setting(self,dict):
        self.exp_time1 = dict["exposure_time1"]
        self.exp_time2 = dict["exposure_time2"]    
        self.numb_accum = 1
        self.kinetic_series_length = 1
        self.numb_prescans = 0
        self.em_gain = 200
        self.aqu_mode = 1
        self.triggering = 0
        self.readmode = 3    #single track
        self.VSSpeed = 1     # 0.3 0.5 0.9 1.7 3.3
        self.VSAmplitude = 0 #0(Normal), +1, +2, +3, +4
        self.adc_chan = 0 
        self.HSSspeed = 0
        self.preamp_gain = 2 # 1.0 2.4 4.9
        self.image_left = 1
        self.image_right = 512
        self.image_bot = 1
        self.image_top = 512
        self.bin_row = dict["row_center"]
        self.bin_height = dict["row_height"]
        self.horizontal_binning = 1
        self.camera.SetShutter(1, 1, 0, 0)
        self.camera.GetTemperature()
        self.camera.SetPreAmpGain(self.preamp_gain)
        self.camera.SetVSSpeed(self.VSSpeed)
        self.camera.SetADChannel(self.adc_chan)
        self.camera.SetEMCCDGain(self.em_gain)
        self.camera.SetAcquisitionMode(self.aqu_mode) # 1 - single scan
        self.camera.SetNumberAccumulations(self.numb_accum)
        self.camera.SetReadMode(self.readmode) # 0 - FVB, 3 - single track
        self.camera.SetSingleTrack(self.bin_row, self.bin_height, self.horizontal_binning)
        self.camera.SetExposureTime(self.exp_time1)
        self.camera.SetTriggerMode(self.triggering)
        self.camera.GetAcquisitionTimings()
        slptm = float(self.camera._kinetic)
        print "sleeptime = ", slptm
        time.sleep(slptm+0.5)

    #Meauring reference detector (photo receiver) dark counts
    def fin_get_dark_level(self, int_time = 500.):
        self.sia.int_time = int_time
        self.sia.configure_devices()
        self.sia.start_cycle()
        dark_level = self.sia.calc_amplitude(darksignal=False)
        return dark_level

    def wait_for_data_acquired(self):
        while self.camera.acqusition_running:
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.005)
        return True	

    #Create folder to save data
    def create_folder(self):
        self.dir_name = "data\\"+str(self.cur_time.year)+str(self.cur_time.month)+str(self.cur_time.day)+"_"+str(self.cur_time.hour)+str(self.cur_time.minute)
        if os.path.exists(self.dir_name): #check if folder already exists
            if os.listdir(self.dir_name): #check if folder is empty
                self.dir_name = self.dir_name+"_1"#change folder name if foder is not empty
                os.makedirs(self.dir_name) #create another foder if foder is not empty
        else:
            os.makedirs(self.dir_name)
    
    def camera_acquisition(self):
        self.camera.StartAcquisition()
        self.camera.WaitForAcquisition()
        self.current_data = self.camera.GetAcquiredData([])
        self.current_data = np.asarray(self.current_data)
        
    def start_measuring(self):
        """
        Parameter definition
        "stokes": Flag for PL measurement. If False, conduct ASPL measurement
        "ref_signal": Reference singal
        "cur_data": emission spectrum from single measurement
        "scan_avg_data": averaged emission spectrum
        "ex_stokes_avg_data": averaged PL spectrum
        "ex_as_avg_data": averaged ASPL spectrum
        "sum_stokes": integrated PL intensity
        "sum_as": integrated ASPL intensity
        """
        refvals = np.zeros(self.N_scans)
        delta = np.abs(self.acton.k_calibr_3*512)  #spectrometer range (nm)
        w_cw = self.wlen_start+(int(delta)-1)/2    #spectrum center wavelength
        grating = self.acton.get_grating()
        if grating != 3:
            print "Change to grating 3"
            self.acton.change_grating("3")
        self.acton.set_wavelength(w_cw, cw=True)
        cur_wlen = (np.arange(1,513,1)*self.acton.k_calibr_3+self.acton.b_calibr_3+self.acton.get_wavelength())
        
        ###get dark level
        print "measuring backgroud"
        self.fianium.set_pwr(0,aotf = "vis")
        self.dio.setoff()
        dark_level_s = self.fin_get_dark_level()
        self.camera_acquisition()
        bckgnd_s = self.current_data
        time.sleep(1)

        ###change camera setting to get dark level of camera for anti-stokes
        self.fw.command("pos=2") #Using filter to clean up PL excitation laser
        print "waiting"
        time.sleep(10) 
        self.camera.SetExposureTime(self.exp_time2)
        time.sleep(0.5)
        self.camera_acquisition()
        bckgnd_as = self.current_data
        self.dio.seton()  
        sum_stokes = np.zeros(self.N_wl_change)  #integrated PL intensity
        sum_as = np.zeros(self.N_wl_change)      #integrated ASPL intensity

        stokes = True       
        for cur_wl_change_n in range(self.N_wl_change):
            if stokes:   #change setup for PL measurement
                self.dio.setoff()
                print "Measuring Stokes Emission"
                self.fw.command("pos=1") #Using filter to clean up stokes excitation
                print "waiting"
                time.sleep(10)
                print "current filter position ", self.fw.query("pos?")   
                self.fianium.set_wlen(self.fianium_stokes_wl, aotf="vis")
                self.fianium.set_pwr(self.fianium_stokes_power,aotf = "vis")
                sia_exp_time = self.exp_time1 *1000./2
                bckgnd = bckgnd_s
                self.dio.seton()
            else:       #change setup for ASPL measurement
                self.dio.setoff()
                print "Measuring Anti-Stokes Emission"
                self.fw.command("pos=2") #Using filter to clean up stokes excitation
                print "waiting"
                time.sleep(10) 
                print "current filter position ", self.fw.query("pos?")  
                self.fianium.set_wlen(self.fianium_as_wl, aotf="vis")
                self.fianium.set_pwr(self.fianium_as_power,aotf = "vis")
                sia_exp_time = self.exp_time2 *1000./2
                bckgnd = bckgnd_as
                self.dio.seton()

            for cur_scan_n in xrange(self.N_scans):
                #get laser power from reference for normalization
                #measuring reference before and after camera measurment
                ref1 = self.sia.ref_amp(sia_exp_time) - dark_level_s  
                self.camera_acquisition()
                cur_data = self.current_data
                ref2 = self.sia.ref_amp(sia_exp_time) - dark_level_s
                ref_signal = (ref1+ref2)/2.
                print "reference", ref_signal
                cur_data = (cur_data - bckgnd)/ref_signal
                refvals[cur_scan_n] = ref_signal
                if cur_scan_n == 0:
                    scan_avg_data = cur_data  
                else:
                    scan_avg_data = (scan_avg_data*cur_scan_n + cur_data)/(cur_scan_n+1)
                if dspl:
                    QtCore.QCoreApplication.processEvents()
            print("ref_signal = %1.5e"%np.mean(ref_signal))
            
               
            if cur_wl_change_n <= 1:
                if stokes:
                    iteration_s = 0
                    ex_stokes_avg_data = scan_avg_data
                    ref_value_s = np.mean(ref_signal)
                    sum_stokes[0] = sum(scan_avg_data)
                    if not self.dspl:
                        stokes = False
                else:
                    iteration_as = 0
                    ex_as_avg_data = scan_avg_data
                    ref_value_as = np.mean(ref_signal)
                    sum_as[0] = sum(scan_avg_data)
                    if not self.dspl:
                        stokes = True
            else:
                if stokes:
                    iteration_s = cur_wl_change_n/2
                    ex_stokes_avg_data = (ex_stokes_avg_data*iteration_s + scan_avg_data)/(iteration_s + 1)
                    ref_value_s = (np.mean(ref_signal) + ref_value_s*iteration_s)/(iteration_s + 1)
                    sum_stokes[iteration_s] = sum(scan_avg_data)
                    if not self.dspl:
                        stokes = False
                else:
                    iteration_as = (cur_wl_change_n - 1)/2
                    ex_as_avg_data = (ex_as_avg_data*iteration_as + scan_avg_data)/(iteration_as + 1)
                    ref_value_as = (np.mean(ref_signal) + ref_value_as*iteration_as)/(iteration_as + 1)
                    sum_as[iteration_as] = sum(scan_avg_data)
                    if not self.dspl:
                        stokes = True
            if self.dspl:
                if stokes:
                    self.stokes_spectra_curve.setData(cur_wlen, ex_stokes_avg_data)
                    self.stokes_sum_curve.setData(np.arange(iteration_s+1),sum_stokes[:iteration_s+1]/max(sum_stokes[:iteration_s+1]))
                    stokes = False
                else:
                    self.as_spectra_curve.setData(cur_wlen, ex_as_avg_data)
                    self.as_sum_curve.setData(np.arange(iteration_as+1),sum_as[:iteration_as+1]/max(sum_as[:iteration_as+1]))
                    stokes = True
                QtCore.QCoreApplication.processEvents()
        self.fianium.set_pwr(0,aotf = "vis")
        self.fw.command("pos=1")
        if self.save:
            self.create_folder()
            #in case number of stokes emission measurement and anti-stokes emission measurement are not same
            if len(sum_as) != len(sum_stokes):
                sum_as.append(0)
            np.savetxt(self.dir_name+'\\'+str(self.cur_time.month)+str(self.cur_time.day)+"_"+str(self.cur_time.hour)+str(self.cur_time.minute)+"_spectra.dat",np.column_stack((cur_wlen,ex_stokes_avg_data,ex_as_avg_data)), fmt='%1.5f', delimiter="\t", header="Wavelength \t Stokes \t Anti-Stokes \n ref = \t %f \t %f"%(ref_value_s, ref_value_as))
            fig = plt.figure(figsize=(3, 6))
            plt.plot(np.arange(iteration_s+1),sum_stokes[:iteration_s+1]/max(sum_stokes[:iteration_s+1]),"r")
            plt.plot(np.arange(iteration_as+1),sum_as[:iteration_as+1]/max(sum_as[:iteration_as+1]),'b')
            fig.savefig(self.dir_name+'\\'+str(self.cur_time.month)+str(self.cur_time.day)+"_"+str(self.cur_time.hour)+str(self.cur_time.minute)+'_power_fluctuation.png')
            
if __name__ == "__main__":

    st = time.time()
    measurement = Stokes_AS(setting_dict_upconversion)
    measurement.start_measuring()
    print time.time()-st