import csv
import threading
import cv2 as cv
import os

DATABASE_PATH = './database.csv'
VIDEOS_PATH = './videos/'

# Stores records of foxes and other animals
class Database():
    def __init__(self, log=False):
        self.lock = threading.Lock()
        self.log = log

    def print_log(self, message):
        if self.log:
            print(message)

    # Save a record into the end of csv file
    def write_record(self, record: list):
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'a', newline='') as file: 
            writer = csv.writer(file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(record)

    # Get a list of all records
    def read_records(self):
        records = []
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'r', newline='') as file:
            reader = csv.reader(file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
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
        video = cv.VideoWriter(VIDEOS_PATH + name + '.mp4', fourcc, float(fps), (width, height))
        for frame in frames:
            video.write(frame)
        
        self.print_log("Finished saving")

    # Delete the database
    def delete_database(self):
        with self.lock, open(DATABASE_PATH, 'w'):
            print('Database deleted')

# Testing
if __name__ == "__main__":
    DATABASE_PATH = '../database.csv'
    VIDEOS_PATH = '../videos/'
    db = Database(log=True)
    db.write_record(['first', 'second', 345])
    db.write_record([''])
    db.write_record(['''this is a loooooooooooong sentence!'''])

    print(db.read_records())
    db.delete_database()
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