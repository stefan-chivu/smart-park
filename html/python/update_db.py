#!/usr/bin/env python

import argparse
import os
import sys
import mysql.connector
import process_image
import logging
import time

def clear_spot(sensorID, db_cursor):
    logging.info("Sensor " + sensorID + " detected car leaving the spot. Setting spot state to empty")
    sql = "SELECT PLATE FROM parking_spots WHERE SPOT_ID='"+sensorID+"' ORDER BY TIME DESC LIMIT 1"
    logging.info(sql)
    db_cursor.execute(sql)
    plate_list = db_cursor.fetchall()
    plate = plate_list[0][0]
    sql = "INSERT INTO parking_spots (SPOT_ID, PLATE, OCCUPIED) VALUES (%s, %s, %s)"
    val = (sensorID, plate,0)
    db_cursor.execute(sql, val)
    logging.info("Cleared spot " + sensorID + " from car with plate [" + plate.upper() + "]")

def occupy_spot(sensorID, image_path, db_cursor):
    logging.info("Sensor " + sensorID + " detected car entering the spot. Setting spot state to occupied")
    plate = ""
    abs_path = os.path.abspath(image_path)
    if os.path.exists(abs_path):
        logging.info("File exists at path: " + abs_path)
        plate = process_image.process(abs_path)
        print("\nPlate: [ " + plate + " ]")
    else:
       logging.error("Invalid file path: File does not exist")

    # Check if car has just changed -- check how to do with sonar
    # maybe double delay
    # check every 5 min if car is parked and retake photo every 10-15 min
    # to see if it's the same car
    logging.info("Sensor " + sensorID + " detected the car changed. Updating spot state")
    sql = "SELECT PLATE FROM parking_spots WHERE SPOT_ID='"+sensorID+"' ORDER BY TIME DESC LIMIT 1"
    logging.info(sql)
    db_cursor.execute(sql)
    existing_plate_list = db_cursor.fetchall()
    if existing_plate_list:
        existing_plate = existing_plate_list[0][0]
        if existing_plate != plate:
            sql = "INSERT INTO parking_spots (SPOT_ID, PLATE, OCCUPIED) VALUES (%s, %s, %s)"
            val = (sensorID, existing_plate,0)
            db_cursor.execute(sql, val)
            time.sleep(3)

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
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])

    logging.basicConfig(filename='update_db.log', level=logging.INFO)

    logging.info("Attempting connection to database")
    db = mysql.connector.connect(
        host="localhost",
        user="admin",
        password="P@ssw0rd!",
        database="parking_info"
    )

    db_cursor = db.cursor()
    logging.info("Succesfully connected to database")

    if parsed_args.spotState == "1":
        occupy_spot(parsed_args.sensorId, parsed_args.inputFile, db_cursor)
    if parsed_args.spotState == "0":
        clear_spot(parsed_args.sensorId, db_cursor)

    db.commit()
    db_cursor.close()
    db.close()
    print("Success")