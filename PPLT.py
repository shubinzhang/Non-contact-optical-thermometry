'''
Instrument control program for monintering temperature change within certain time interval using pump-probe luminescence thermometry (PPLT), 
more information can be found in following link https://aip.scitation.org/doi/abs/10.1063/1.4811759

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
from Lib import andor_camera
from PyQt4 import QtCore, QtGui
import pyqtgraph andor_ixonas pg
import numpy as np
from datetime import datetime as dt
import matplotlib.pyplot as plt

class PPLT():
    def __init__(self,setting_dict,dspl):
        self.cur_time = dt.now()
        self.app = QtGui.QApplication(sys.argv)
        self.camera = andor_camera.AndorCamera()  #connect ccd camera
        self.camera_cooldown()
        self.camera_setting(setting_dict)
        self.acton = acton.Acton(setting_dict["acton_port"], grating = 3) #connect spectrometer
        self.fianium = fianium_py.fianium_aotf()  #connect laser
        self.get_aqu_setting(setting_dict)
        self.fianium.enable()
        self.dspl = dspl
        if self.dspl:   #Show PL/ASPL spctrum as well as integrated intensity
            self.ploto1 = pg.plot()
            self.ploto2 = pg.plot()
            self.ploto1.showGrid(x=True, y=True, alpha=1.)
            self.ploto2.showGrid(x=True, y=True, alpha=1.)
            self.temperature_curve = self.ploto1.plot(pen = pg.mkPen('r', width=1.5))
            self.spectrum = self.ploto2.plot(pen = pg.mkPen('r', width=1.5))

    def get_aqu_setting(self,dict):
        self.wlen_start = float(dict["wlen_start"])
        self.slit = 20  #default value
        self.N_average = int(dict["N_average"])
        self.N_measurement = int(dict["N_measurement"])
        self.laser_wlen = int(dict["wl"])
        self.laser_power = int(dict["power"])
        self.slp_time = int(dict["waiting_time"])

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
            sleep(0.1)
            cur_T = float(self.camera._temperature)
            print "current Temperature is ", cur_T
            print "current status ", self.camera.GetTemperature()
            sleep(10)
        print "Temperature is stable now"
    
    #Set up camera
    def camera_setting(self,dict):
        self.exp_time1 = dict["exposure_time"]
        self.numb_accum = 1
        self.kinetic_series_length = 1
        self.numb_prescans = 0
        self.em_gain = 0
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
        sleep(slptm+0.5)

    #Correlation function between weighted emission wavelength and temperature, can be different for differnt materials
    def Tcurve(self, wlen):
        T = (wlen-569.523)/0.0834
        return T

    def wait_for_data_acquired(self):
        while self.camera.acqusition_running:
            QtCore.QCoreApplication.processEvents()
            sleep(0.005)
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
        
    def start_measuring(self,save):
         """
        Parameter definition
        

        "cur_data": emission spectrum from single measurement
        "scan_avg_data": averaged emission spectrum
        "average_wlen": weighted emission wavelength
        "temperature": current temperature based on average emission wavelength 
        """
        if save:
            self.create_folder()
        stime = time.time()
        delta = np.abs(self.acton.k_calibr_3*512)   #spectrometer range (nm)
        w_cw = self.wlen_start+(int(delta)-1)/2     #spectrum center wavelength
        grating = self.acton.get_grating()
        if grating != 3:
            print "Change to grating 3"
            self.acton.change_grating("3")
        self.acton.set_wavelength(w_cw, cw=True)
        cur_wlen = (np.arange(1,513,1)*self.acton.k_calibr_3+self.acton.b_calibr_3+self.acton.get_wavelength())
        
        ###get dark level
        print "measuring backgroud"
        self.fianium.set_pwr(0,aotf = "vis")
        self.camera_acquisition()
        bckgnd = self.current_data
        self.fianium.set_wlen(self.laser_wlen , aotf="vis")
        self.fianium.set_pwr(self.laser_power,aotf = "vis")
        temperature_list = []
        time_list = []
        for index in xrange(self.N_measurement):
            for cur_scan_n in xrange(self.N_average):
                self.fianium.set_pwr(self.laser_power,aotf = "vis")
                self.camera_acquisition()
                cur_data = self.current_data
                cur_data = cur_data - bckgnd
                if cur_scan_n == 0:
                    scan_avg_data = cur_data
                else:
                    scan_avg_data = (scan_avg_data*cur_scan_n + cur_data)/(cur_scan_n+1)
                if dspl:
                    self.spectrum.setData(cur_wlen, scan_avg_data)
                    QtCore.QCoreApplication.processEvents()
            average_wlen = sum(cur_wlen*scan_avg_data)/sum(scan_avg_data)
            temperature = self.Tcurve(average_wlen)
            cur_time = (time.time()-stime)/60.
            temperature_list.append(temperature)
            time_list.append(cur_time)
            if dspl:
                self.temperature_curve.setData(time_list, temperature_list)
                QtCore.QCoreApplication.processEvents()
            self.fianium.set_pwr(0,aotf = "vis")
            print "current wavelength is ", average_wlen
            print "current sample temperature is", temperature
            print "waiting for ", self.slp_time, "s"
            sleep(self.slp_time)

            if save:
                np.savetxt(self.dir_name+'\\'+str(self.cur_time.month)+str(self.cur_time.day)+"_"+str(self.cur_time.hour)+str(self.cur_time.minute)+"__"+str(index)+"_spectra.dat",np.column_stack((cur_wlen, scan_avg_data)), fmt='%1.5f', delimiter="\t" )
                np.savetxt(self.dir_name+'\\'+str(self.cur_time.month)+str(self.cur_time.day)+"_"+str(self.cur_time.hour)+str(self.cur_time.minute)+"_temperatuer.dat",np.column_stack((time_list,temperature_list)), fmt='%1.5f', delimiter="\t" )


if __name__ == "__main__":
    st = time.time()
    measurement = PPLT(setting_dict,dspl)
    measurement.start_measuring(save)
    print time.time()-st