#!/usr/bin/python
# ---------------------------------------------------------------
# This Python Script reads out bme280 and senseair s8 sensors on
# the Rasberry Pi3 for a (by User-defined) time. Once the data is
# collected, it is written to a .tab file and a Plot is generated.
# This script was written by Reto Läderrach and Etienne Schmelzer.
# ---------------------------------------------------------------
#
# In order to install pandas on linux systems:
# sudo apt-get install python3-pandas
# activate the interfaces for the sensors
#
# Temp-Sensor:
# sudo raspi-config
# -> Interfacing Options:
#  ->activate i2c
#
# Co2-Sensor:
# sudo raspi-config
# -> Interfacing Options:
#  ->activate serial
#   -> "No" when it asks if you want a login shell over serial
#    -> "Yes" when asked if you want hte hardware enabled
#     -> "yes" to reboot

import pandas as pd
import datetime
import time
import serial
import smbus
from ctypes import c_short
from ctypes import c_byte
from ctypes import c_ubyte
import matplotlib.pyplot as plt
import random

class bme280(object):
    """
    This class allows to readout temperature, humidity and
    pressure from the sensor bme280:
    https://www.bosch-sensortec.com/bst/products/all_products/bme280
    This class was generated based on a scirpt by Matt Hawkins.
    https://www.raspberrypi-spy.co.uk/
    """
    def __init__(self):
        
        self.DEVICE = 0x76 # Default device I2C address
        self.bus = smbus.SMBus(1) # Rev 2 Pi, Pi 2 & Pi 3 uses bus 1
                                    # Rev 1 Pi uses bus 0
        try:
            self.read()
            print("Bme280 initialized")
        except:
            print("Bme280 not connected")
                     

    def getShort(self, data, index):
        # return two bytes from data as a signed 16-bit value
        return c_short((data[index+1] << 8) + data[index]).value

    def getUShort(self, data, index):
        # return two bytes from data as an unsigned 16-bit value
        return (data[index+1] << 8) + data[index]

    def getChar(self, data,index):
        # return one byte from data as a signed char
        result = data[index]
        if result > 127:
          result -= 256
        return result

    def getUChar(self, data,index):
        # return one byte from data as an unsigned char
        result =  data[index] & 0xFF
        return result

    def readID(self):
        # Chip ID Register Address
        REG_ID     = 0xD0
        (chip_id, chip_version) = self.bus.read_i2c_block_data(self.DEVICE, REG_ID, 2)
        return (chip_id, chip_version)

    def read(self):
        # Register Addresses
        REG_DATA = 0xF7
        REG_CONTROL = 0xF4
        REG_CONFIG  = 0xF5

        REG_CONTROL_HUM = 0xF2
        REG_HUM_MSB = 0xFD
        REG_HUM_LSB = 0xFE

        # Oversample setting - page 27
        OVERSAMPLE_TEMP = 2
        OVERSAMPLE_PRES = 2
        MODE = 1

        # Oversample setting for humidity register - page 26
        OVERSAMPLE_HUM = 2
        self.bus.write_byte_data(self.DEVICE, REG_CONTROL_HUM, OVERSAMPLE_HUM)

        control = OVERSAMPLE_TEMP<<5 | OVERSAMPLE_PRES<<2 | MODE
        self.bus.write_byte_data(self.DEVICE, REG_CONTROL, control)

        # Read blocks of calibration data from EEPROM
        # See Page 22 data sheet
        cal1 = self.bus.read_i2c_block_data(self.DEVICE, 0x88, 24)
        cal2 = self.bus.read_i2c_block_data(self.DEVICE, 0xA1, 1)
        cal3 = self.bus.read_i2c_block_data(self.DEVICE, 0xE1, 7)

        # Convert byte data to word values
        dig_T1 = self.getUShort(cal1, 0)
        dig_T2 = self.getShort(cal1, 2)
        dig_T3 = self.getShort(cal1, 4)

        dig_P1 = self.getUShort(cal1, 6)
        dig_P2 = self.getShort(cal1, 8)
        dig_P3 = self.getShort(cal1, 10)
        dig_P4 = self.getShort(cal1, 12)
        dig_P5 = self.getShort(cal1, 14)
        dig_P6 = self.getShort(cal1, 16)
        dig_P7 = self.getShort(cal1, 18)
        dig_P8 = self.getShort(cal1, 20)
        dig_P9 = self.getShort(cal1, 22)

        dig_H1 = self.getUChar(cal2, 0)
        dig_H2 = self.getShort(cal3, 0)
        dig_H3 = self.getUChar(cal3, 2)

        dig_H4 = self.getChar(cal3, 3)
        dig_H4 = (dig_H4 << 24) >> 20
        dig_H4 = dig_H4 | (self.getChar(cal3, 4) & 0x0F)

        dig_H5 = self.getChar(cal3, 5)
        dig_H5 = (dig_H5 << 24) >> 20
        dig_H5 = dig_H5 | (self.getUChar(cal3, 4) >> 4 & 0x0F)

        dig_H6 = self.getChar(cal3, 6)

        # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
        wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + ((2.3 * OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM)+0.575)
        time.sleep(wait_time/1000)  # Wait the required time  

        # Read temperature/pressure/humidity
        data = self.bus.read_i2c_block_data(self.DEVICE, REG_DATA, 8)
        pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        hum_raw = (data[6] << 8) | data[7]

        #Refine temperature
        var1 = ((((temp_raw>>3)-(dig_T1<<1)))*(dig_T2)) >> 11
        var2 = (((((temp_raw>>4) - (dig_T1)) * ((temp_raw>>4) - (dig_T1))) >> 12) * (dig_T3)) >> 14
        t_fine = var1+var2
        temperature = float(((t_fine * 5) + 128) >> 8);

        # Refine pressure and adjust for temperature
        var1 = t_fine / 2.0 - 64000.0
        var2 = var1 * var1 * dig_P6 / 32768.0
        var2 = var2 + var1 * dig_P5 * 2.0
        var2 = var2 / 4.0 + dig_P4 * 65536.0
        var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * dig_P1
        if var1 == 0:
            pressure=0
        else:
            pressure = 1048576.0 - pres_raw
            pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
            var1 = dig_P9 * pressure * pressure / 2147483648.0
            var2 = pressure * dig_P8 / 32768.0
            pressure = pressure + (var1 + var2 + dig_P7) / 16.0

        # Refine humidity
        humidity = t_fine - 76800.0
        humidity = (hum_raw - (dig_H4 * 64.0 + dig_H5 / 16384.0 * humidity)) * (dig_H2 / 65536.0 * (1.0 + dig_H6 / 67108864.0 * humidity * (1.0 + dig_H3 / 67108864.0 * humidity)))
        humidity = humidity * (1.0 - dig_H1 * humidity / 524288.0)
        if humidity > 100:
            humidity = 100
        elif humidity < 0:
            humidity = 0

        return temperature/100.0,pressure/100.0,humidity


class senseair(object):
    """
    Class for Co2 sensor "senseair s8". It allows to readout the Co2 concentration.
    Link ----
    
    """
    
    def __init__(self):
        self.ser = serial.Serial("/dev/ttyS0",baudrate =9600,timeout = 0.5)
            
        try:
            self.read()
            print("Senseair S8 initialized")
        except:
            print("Senseair S8 not connected") 
        
    def read(self):  
        """
        This method returns the Co2 concentration in ppm
        """
        self.ser.flushInput()
        self.ser.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
        resp = self.ser.read(7)
        high = resp[3]
        low = resp[4]
        co2 = (high*256) + low
        return co2

class sensors(object):
    
    def __init__(self):
        #Initializing bme280
        self.bme = bme280()
        #Initializing sensair s8
        self.senseair_s8 = senseair()
        

    def measure(self):
        """
        This function reads out the sensors and adds them to the dataframe. The index is a timestamp index.
        
        """ 
        try:
            co2=self.senseair_s8.read()
        except:
            co2 = None
        
        try:
            temperature,pressure,humidity = self.bme.read()
            humidity = round(humidity, 2)
        except:
            temperature, pressure, humidity = (None, None, None)


        return (co2, temperature, humidity)
        

def setting_up_dataframe(columns):
    """
    Sets up a dataframe with a timestamp index and the columns temperature, humidity and Co2.
    """
    
    df = pd.DataFrame(columns=columns, index=pd.to_datetime([]))
    return df


def harryplotter(df, outfilename):
    """
    Plots the collected data.
    df = Dataframe
    outfilename = filepath and Name
    """
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(10, 10))

    f0 = df.iloc[:, 0].plot(ax=axes[0, 0])
    f0.set_title("Temperature")
    f0.set_xlabel("Time")
    f0.set_ylabel("C")

    f1 = df.iloc[:, 1].plot(ax=axes[0, 1])
    f1.set_title("Humidity")
    f1.set_xlabel("Time")
    f1.set_ylabel("Humidity")

    f2 = df.iloc[:, 2].plot(ax=axes[1, 0])
    f2.set_title("Co2 concentration")
    f2.set_xlabel("Time")
    f2.set_ylabel("Co2 in ppm")

    f3 = df.iloc[:, 0:3].plot(ax=axes[1, 1], logy=True)
    f3.set_title("All measurments")
    f3.set_xlabel("Time")
    plt.tight_layout()
    plt.savefig("{}_plots.pdf".format(outfilename))



def run_analysis():
    # Settings:
    try:
        z = int(input("For how many minutes do you want to take the measurements? (in min, only int)\n>"))
    except ValueError:
        z = int(input("Please insert an integer!\n For how many minutes do you want to measure\n>"))

    # The time intervall between each measurments
    t_sleep = 1
    m = int(z * 60 / t_sleep)

    outfilename = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S_Measurments")

    # setting up the Dataframe:
    df = setting_up_dataframe(["temperature", "humidity", "Co2(ppm)"])
    
    # Initializing sensors
    s=sensors()
    
    for i in range(0, m):
        co2, temperature, humidity = s.measure()
        df.loc[pd.Timestamp('now').strftime("%Y-%m-%d %H:%M:%S")] = [temperature, humidity, co2]
        now = pd.Timestamp('now').strftime("%Y-%m-%d %H:%M:%S")
        print("{}/{}, {}   {} ppm, {}°C, {}%".format(i+1, m, now, co2, temperature, humidity))
        time.sleep(t_sleep)

    # writing the dataframe to an excel file
    df.to_csv(outfilename + ".tab", sep='\t')
    
    # plotting the data and saving
    harryplotter(df, outfilename)


if __name__=="__main__":

    run_analysis()
    





