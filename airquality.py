#!/usr/bin/python
# ---------------------------------------------------------------
# This Python Script reads out bme280 and senseair s8 sensors on
# the Rasberry Pi3 for a (by User-defined) time. Once the data is
# collected, it is written to a .tab file and a Plot is generated.
# This script was written by Reto Läderrach and Etienne Schmelzer.
# Note: Please make sure that you have the airsensors.py in the
# same folder as this script.
# ---------------------------------------------------------------

import pandas as pd
import time
from datetime import datetime
from airsensors import sensors
import matplotlib.pyplot as plt

      

def setting_up_dataframe(columns):
    """
    Sets up a dataframe with a timestamp index and the defined columns.
    columns= List
    """
    
    df = pd.DataFrame(columns=columns, index=pd.to_datetime([]))
    return df


def harryplotter(df, outfilename):
    """
    Plots the collected data.
    df = pd.Dataframe
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

    outfilename = datetime.now().strftime("%Y_%m_%d-%H_%M_%S_Measurments")

    # setting up the Dataframe:
    df = setting_up_dataframe(["temperature", "humidity", "Co2(ppm)"])
    
    # Initializing sensors
    s=sensors()
    
    for i in range(0, m):
        # Measuring Co2, temperature and humidity
        co2, temperature, humidity = s.read()
        # Writing the Data into the Dataframe
        #df.loc[pd.Timestamp('now').strftime("%Y-%m-%d %H:%M:%S")] = [temperature, humidity, co2]
        df.loc[pd.Timestamp('now')] = [temperature, humidity, co2]
        # Producing a nice print statement:
        
        now = pd.Timestamp('now').strftime("%Y-%m-%d %H:%M:%S")
        print("{}/{}, {}   {} ppm, {}°C, {}%".format(i+1, m, now, co2, temperature, humidity))
        # waiting until next measurment
        time.sleep(t_sleep)

    # writing the dataframe to an excel file
    df.to_csv(outfilename + ".tab", sep='\t')
    
    # plotting the data and saving
    harryplotter(df, outfilename)


if __name__=="__main__":
    # Let's run analysis
    run_analysis()
    





