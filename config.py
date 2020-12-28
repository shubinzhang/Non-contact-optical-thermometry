#Settings for up-conversion thermometry
setting_dict_upconversion = {
    #Instrument connection setting
    "chromex_port": 1  #spectrometer port number
    "filter_wheel": 2  #filter wheel port number
    "shutter_port": 3  #shutter port number
    "shutter_line": 1  #shutter line number 

    #Measuremnt setting
    "wlen_start":450,  #start wavelength of spectrum
    "N_scans":8,       #number of spectra measured for averaging
    "N_wl_change":10,  #number of PL/ASPL spectra measured each time 
    "wl1":460,         #excitation wavelength for PL
    "wl2":542,         #excitation wavelength for ASPL 
    "power1":20,       #Laser power for PL %
    "power2":100,      #Laser power for ASPL %
    "exposure_time1": 0.3,  #exposure time of CCD camera for PL (s)
    "exposure_time2":0.3,   #exposure time of CCD camera for ASPL (s)
    "row_center":258,  #vertial position of emission spot in CCD camera iamge 
    "row_height":11,   #emission spot height in CCD camera iamge
    "dspl" = True,     #show PL/ASPL spectra during measurement     
    "save" = True,     #save data
    } 

#Settings for PPLT
setting_dict_upconversion = {
    #Instrument connection setting
    "chromex_port": 1  #spectrometer port number 

    #Measuremnt setting
    "wlen_start":450,   #start wavelength of spectrum
    "N_scans":8,        #number of spectra measured for averaging
    "N_measurement":10, #number of temperature measurement
    "waiting_time":15,  #waiting time between each measurement (s)
    "wl":542,           #excitation wavelength
    "power":20,         #Laser power %
    "exposure_time": 0.3,  #exposure time of CCD camera (s)
    "row_center":258,  #vertial position of emission spot in CCD camera iamge
    "row_height":11,   #emission spot height in CCD camera iamge
    "dspl" = True,     #show PL/ASPL spectra during measurement     
    "save" = True,     #save data
    } 