#!/usr/bin/env python

import argparse
import os
import sys
import mysql.connector
import process_image
import logging
import time

# Function to update the sensor's occupancy status to 0 (empty) in the database
def clear_spot(sensorID, db_cursor):
    logging.info("Sensor " + sensorID + " detected car leaving the spot. Setting spot state to empty")

    # Fetch the current state of the spot from the database
    sql = "SELECT PLATE FROM parking_spots WHERE SPOT_ID='"+sensorID+"' ORDER BY TIME DESC LIMIT 1"
    logging.info(sql)
    db_cursor.execute(sql)
    plate_list = db_cursor.fetchall()
    if len(plate_list) < 1:
        # if there are no entries coresponding to the sensor with ID: sensorID, exit the function
        # since there is nothing to clear
        return
    
    # get the current plate corresponding to the sensor in the DB
    plate = plate_list[0][0]

    # set the spot state to 0 (empty) and mark the exit of the current vehicle
    sql = "INSERT INTO parking_spots (SPOT_ID, PLATE, OCCUPIED) VALUES (%s, %s, %s)"
    val = (sensorID, plate,0)
    db_cursor.execute(sql, val)
    logging.info("Cleared spot " + sensorID + " from car with plate [" + plate.upper() + "]")

# Function to update the sensor's occupancy status to 1 (occupied) in the database
def occupy_spot(sensorID, image_path, db_cursor):
    # Boolean flag to check if the car has changed
    inserted = False

    logging.info("Sensor " + sensorID + " detected car entering the spot. Setting spot state to occupied")
    plate = "N/A"

    abs_path = os.path.abspath(image_path)
    if os.path.exists(abs_path):
        logging.info("File exists at path: " + abs_path)
        # Send the image at image_path to be proccessed by the PlateRecognizer API
        plate = process_image.process(abs_path)
        print("\nPlate: [ " + plate + " ]")
    else:
       logging.error("Invalid file path: File does not exist")

    # Check if car has just changed by getting the current state of the sensor in the DB
    sql = "SELECT PLATE, OCCUPIED FROM parking_spots WHERE SPOT_ID='"+sensorID+"' ORDER BY TIME DESC LIMIT 1"
    logging.info(sql)
    db_cursor.execute(sql)

    existing_plate_list = db_cursor.fetchall()

    # if the sensor already has corresponding data in the database
    # check the existing state and plate
    if len(existing_plate_list) > 0:
        existing_plate = existing_plate_list[0][0]
        occupied = existing_plate_list[0][1]

        # if the sensor is already marked as occupied, check if car is the same
        if occupied == 1:
            print("Existing:" + existing_plate)
            print("New:" + plate)
            print("Occupied: " + str(occupied))

            # if the car has changed, insert the exit for the previous car and
            # occupy the spot for the new car
            if existing_plate != plate:
                print("Plates do not match... Car has changed")
                logging.info("Sensor " + sensorID + " detected the car changed. Updating spot state")
                sql = "INSERT INTO parking_spots (SPOT_ID, PLATE, OCCUPIED) VALUES (%s, %s, %s)"
                val = (sensorID, existing_plate,0)
                db_cursor.execute(sql, val)
                time.sleep(3)
            else:
                # if the spot is still occupied by the same car, don't insert another 1 in the DB
                inserted = True
                
    # insert 1 if the spot is empty or if the spot is occupied by a different car
    if not inserted:
        sql = "INSERT INTO parking_spots (SPOT_ID, PLATE, OCCUPIED) VALUES (%s, %s, %s)"
        val = (sensorID, plate,1)
        db_cursor.execute(sql, val)



def create_arg_parser():
    # Creates and returns the ArgumentParser object
    parser = argparse.ArgumentParser(description='Script to proces images using Plate Recognizer')

    parser.add_argument('sensorId',
                    help='The ID of the sensor that sent the picture')
    parser.add_argument('spotState',
                    help='The current state of the parking spot')
    parser.add_argument('inputFile',
                    help='Path to the image')          

    return parser

if __name__ == "__main__":
    # parse the program arguments
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])

    logging.basicConfig(filename='update_db.log', level=logging.INFO)

    logging.info("Attempting connection to database")

    # connect to the SQL database
    db = mysql.connector.connect(
        host="localhost",
        user="admin",
        password="P@ssw0rd!",
        database="parking_info"
    )

    db_cursor = db.cursor()
    logging.info("Succesfully connected to database")

    # if the spot state is 1, then the spot is occupied
    if parsed_args.spotState == "1":
        # trigger the spot occupation function
        occupy_spot(parsed_args.sensorId, parsed_args.inputFile, db_cursor)
    if parsed_args.spotState == "0":
        # clear the spot state in the database
        clear_spot(parsed_args.sensorId, db_cursor)

    # commit the database changes to the SQL server
    db.commit()
    db_cursor.close()
    db.close()
    print("Success")