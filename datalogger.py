#!/usr/bin/python
# ---------------------------------------------------------------
# This script uses the airsensors.py module to readout the bme280
# and senseair S8 sensor. The acquired data is saved to the user-
# defined database.
# ---------------------------------------------------------------
# Note: Please make sure that you have the airsensors.py in the
# same folder as this script.



import psycopg2
from psycopg2 import sql
from datetime import datetime
import time
from airsensors import sensors

class airqualityDB(object):
    
    def __init__(self, dbname, table):
        # Connecting to the Database
        try:
            self.conn = psycopg2.connect(database=dbname)
            print("Connected to database")
        except:
            print("Could not connect to database")
        self.cur = self.conn.cursor()
        # Connecting to the desired Table
        self.table = table
        try:
            self.cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(self.table)))
            print("Connected to table")
        except:
            print("Connection to table could not be established")

        
    def add(self, date, temperature, humidity, co2):
        # Addition of the new measurment to the Database
        query = sql.SQL("""
        INSERT INTO
        {}
        VALUES
        (%s, %s, %s, %s)
        """).format(sql.Identifier(self.table))
        values = [date, temperature, humidity, co2]
        self.cur.execute(query, values)
        self.conn.commit()
        print("{} Measurment has been added".format(self.cur.rowcount))
        
    def show(self):
        #Displaying the data
        self.cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(self.table)))
        results = self.cur.fetchall()
        for result in results:
            print(result)
    
    def close(self):
        #closing the connection
        self.conn.close()
 
        
if __name__=="__main__":
    
    s=sensors()
    db = airqualityDB("airquality", "avenue")
    # change -> to a while loop and make the python script autostart 
    m=5
    t_sleep = 1
    for i in range(0, m):
        # Measuring Co2, temperature and humidity
        co2, temperature, humidity = s.read()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("{}/{}, {}   {} ppm, {}°C, {}%".format(i+1, m, now, co2, temperature, humidity))
        
        # Writing the Data into the Dataframe
        db.add(now, temperature, humidity, co2)

        # waiting until next measurment
        time.sleep(t_sleep)
    # Displaying all values
    db.show()
    # Displaying the 
    db.close()





