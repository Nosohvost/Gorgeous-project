import csv
import threading
import cv2 as cv
import os
import pandas as pd
import random
import time

DATABASE_PATH = './database.csv'
VIDEOS_PATH = './videos/'

# Stores records of foxes and other animals
class Database():
    def __init__(self, log=False):
        self.lock = threading.Lock()
        self.log = log
        self.header = ['Unix time', 'Date', 'Label']

    def print_log(self, message):
        if self.log:
            print(message)

    # Save a record into the end of csv file
    def write_record(self, record: dict):
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'a', newline='') as file: 
            writer = csv.DictWriter(file, delimiter=',', 
                                    quoting=csv.QUOTE_MINIMAL, fieldnames=self.header)
            writer.writerow(record)

    # Get records as a list of dictionaries
    def read_records(self):
        records = []
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'r', newline='') as file:
            reader = csv.DictReader(file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                records.append(row)
        return records
    
    # Converts a list of frames to mp4 video and saves it
    def save_video(self, frames: list, name, fps):
        os.makedirs(VIDEOS_PATH, exist_ok=True) # Make sure the directory exists

        # Get the dimensions and fourCC
        height, width, channels = frames[0].shape
        fourcc = cv.VideoWriter_fourcc(*'mp4v')
        self.print_log(f"Started saving a video, height: {height}, width: {width}")


        # Create the video
        try:
            video = cv.VideoWriter(VIDEOS_PATH + name + '.mp4', fourcc, float(fps), (width, height))
            for frame in frames:
                video.write(frame)
            self.print_log("Finished saving")
        except:
            self.print_log(f"Error occurred during saving, skipping")

    # Delete the database
    def delete_database(self):
        with self.lock, open(DATABASE_PATH, 'w') as file:
            writer = csv.DictWriter(file, delimiter=',', 
                                    quoting=csv.QUOTE_MINIMAL, fieldnames=self.header)
            writer.writeheader()
            print('Database deleted')

    # Put random entries in database
    def random_database(self, n):
        self.delete_database()
        for i in range(n):
            unix_time = random.randint(0, 50000000)
            date = 'N/A'
            label = random.choice(['Fox', 'Cat'])
            self.write_record({'Unix time': unix_time,
                               'Date': date,
                               'Label': label})
            

# Testing
if __name__ == "__main__":
    DATABASE_PATH = '../database.csv'
    VIDEOS_PATH = '../videos/'
    db = Database(log=True)
    
    if input("WARNING: the database will be deleted. Are you sure you want to proceed? ").lower() !=  "yes":
        quit()

    db.delete_database()
    db.write_record({'Unix time': 123, 'Date': '01/02/23 13:31:10', 'Label': 'Monster'})
    db.write_record({'Unix time': 456789, 'Date': '24/12/23 19:53:14', 'Label': 'Santa'})
    print(db.read_records())
    
    print('Reading rtsp stream')
    frames = []
    cam = cv.VideoCapture("rtsp://username:spying_on_foxes@192.168.0.211:554/stream1")
    i = 0
    success, frame = cam.read()
    for i in range(0, 30):
        frames.append(frame)
        success, frame = cam.read()
    print('Saving video')
    db.save_video(frames, 'test_video', 14)
    print('Video saved')