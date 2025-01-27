import os
if os.name == 'nt': # Fix for windows and fastai library
    import pathlib
    pathlib.PosixPath = pathlib.WindowsPath

from fastai.vision.all import *
import cv2 as cv
import threading
import numpy as np
from src import dbutils
import datetime
import time

LEARNER_PATH = './NN.pkl'

# A classifier based on CNN that identifies object on a video/image
# Possible options: Empty; Human; Cat; Dog; Fox
class Classifier():
    def __init__(self):
        self.LEARNER_PATH = LEARNER_PATH
        self.learner = load_learner(self.LEARNER_PATH)
        self.MSE_THRESHOLD = 20

        # Number of pixels to crop each side
        self.top_crop = 100
        self.bottom_crop = 10
        self.left_crop = 0
        self.right_crop = 50

    # Crops frame by n pixels in each direction
    def crop_frame(self, frame, top_crop, bottom_crop, left_crop, right_crop):
        return frame[top_crop : frame.shape[0] - bottom_crop, 
                     left_crop : frame.shape[1] - right_crop]
    
    # Calculates MSE between two frames
    def mse(self, frame1, frame2):
        # Cast uint8 to int32 to avoid overflow
        frame1 = frame1.astype(np.int32)
        frame2 = frame2.astype(np.int32)
    
        assert frame1.shape == frame2.shape, "Shapes do not match"

        # Calculate MSE
        mse = np.mean((frame1 - frame2) ** 2)
        return mse
    
    # Classifies a video. Video must be a list of frames
    def classify_video(self, video):
        predictions = {'Empty': 0,
                       'Human': 0,
                       'Cat'  : 0,
                       'Dog'  : 0,
                       'Fox'  : 0}

        # Get predictions for each frame
        for i, frame in enumerate(video):
            if self.mse(video[i - 1], frame) > self.MSE_THRESHOLD:
                transformed_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB) # Convert from BGR to RGB
                transformed_frame = self.crop_frame(transformed_frame, self.top_crop, self.bottom_crop, self.left_crop, self.right_crop) # Crop the frame
                predictions[self.classify_img(transformed_frame)] += 1

        # Return 'Empty' if >90% of frames are classified as empty
        empty_count = predictions['Empty']
        predictions['Empty'] = 0
        if (empty_count / len(video) > 0.95):
            return 'Empty'
        
        # Else return most popular prediction
        else:
            return max(predictions, key=predictions.get) # Get the key with maximum value

    # Classifies a single image
    def classify_img(self, img):
        label = self.learner.predict(img)[0]
        return label


class Camera():
    def __init__(self, rtsp_url, database, start_time: datetime.datetime, end_time: datetime.datetime, log=False):
        self.rtsp_url = rtsp_url
        self.classifier = Classifier()
        self.db = database
        self.log = log
        self.start_time = start_time
        self.end_time = end_time

        # Fps in saved videos
        self.fps = 14

    # Prints message only of logging is turned on
    def print_log(self, message):
        if self.log:
            print(message)

    # Calculates MSE between two frames
    def mse(self, frame1, frame2):
        # Cast uint8 to int32 to avoid overflow
        frame1 = frame1.astype(np.int32)
        frame2 = frame2.astype(np.int32)
    
        assert frame1.shape == frame2.shape, "Shapes do not match"

        # Calculate MSE
        mse = np.mean((frame1 - frame2) ** 2)
        return mse
    
    # Read 1 frame from a camera
    def read_frame(self):
        try:
            success, frame = self.cam.read()
            return success, frame
        except:
            return False, None
    
    # Start looking for movement on the camera
    def start(self, end: threading.Event, mse_threshold=20, consequent_frames_threshold=4):
        ''' Starts looking for movement on a camera until stopped by main program
            or an error occurs. When MSE between <n> consequent frames exceeds threshold,
            the next 70 frames (~5 seconds) and 30 previous are recorded. When frames are finished recording,
            they are passed to Classifier which assigns a label. If the label is not empty, 
            mp4 file is created and saved, and the database is updated'''

        # Connect to the camera
        self.print_log(f"Connecting to camera at {self.rtsp_url}")
        self.cam = cv.VideoCapture(self.rtsp_url)
        self.print_log(f"Finished connecting")

        frames_to_save = []
        success, new_frame = self.read_frame()
        consequent_frames = 0
        to_be_saved = 0
        frames_queue = [new_frame] * 30 # Fill the queue with the first frame
        consequent_failed = 0 # Number of consequent frames that failed to load

        # Keep reading new frames until either stopped by main program or error occurs
        while self.cam.isOpened() and not end.is_set():
            # If current time is not during working hours, skip the whole loop
            current_time = datetime.datetime.now()
            start_today = current_time.replace(hour=self.start_time.hour, minute=self.start_time.minute)
            end_today = current_time.replace(hour=self.end_time.hour, minute=self.end_time.minute)
            if (start_today < end_today and (current_time < start_today or end_today < current_time)) or (
                start_today > end_today and (current_time < start_today and end_today < current_time)):
                #self.print_log(f"Outside working hours, sleeping at {current_time}")
                time.sleep(1) # Sleep to not load the CPU
                continue

            # Update the number of consequent frames which exceeded MSE threshold (or reset to 0)
            if self.mse(frames_queue[-1], frames_queue[-2]) > mse_threshold:
                consequent_frames += 1
            else:
                consequent_frames = 0

            # Queue 100 (30 previous + 70 next) frames to be saved if enough consequent frames show movement
            if (consequent_frames > consequent_frames_threshold):
                self.print_log("Queueing 100 frames to be saved")
                to_be_saved = 100

            # Save the current frame if queued
            if to_be_saved > 0:
                to_be_saved -= 1
                frames_to_save.append(frames_queue[0])

            # Process the frames when they are finished recording
            elif len(frames_to_save) != 0:
                self.print_log("Finished recording frames, starting processing")
                self.process_frames(frames_to_save)
                frames_to_save = []

            # Read a new frame and update the queue
            success, new_frame = self.read_frame()
            if success:
                consequent_failed = 0
                frames_queue.append(new_frame)
                frames_queue.pop(0)
            else:
                consequent_failed += 1
                self.print_log("Failed to read new frame")
                # Restart the camera if many frames couldn't be loaded
                if consequent_failed > 3:
                    self.cam.release()
                    self.print_log("Reconnecting to camera")
                    self.cam = cv.VideoCapture(self.rtsp_url)
                    self.print_log("Reconnected successfully")
                    consequent_failed = 0
                
        self.print_log('Exiting camera')
        self.cam.release()
        cv.destroyAllWindows()

    # Classifies a video with neural net 
    def process_frames(self, frames):
        # Get a prediction
        pred = self.classifier.classify_video(frames)
        self.print_log(f'Object labeled as {pred}')
        
        # Save only cats and foxes
        if pred not in ('Cat', 'Fox'):
            return
        
        unix_time = int(time.time())
        formatted_time = time.strftime("%d/%m/%y %H:%M:%S") # Date in more human-readable format
        file_name_time = time.strftime("%d-%m-%y %Hh %Mm %Ss") # Time for file name
        video_name = pred + " " + file_name_time
        self.db.write_record({'Unix time': unix_time, 
                              'Date': formatted_time, 
                              'Label': pred})
        self.db.save_video(frames, video_name, self.fps)


# Testing
if __name__ == "__main__":
    USERNAME = 'username'
    PASSWORD = 'spying_on_foxes'
    IP_ADDRESS = "192.168.0.211"
    PORT = '554'
    RTSP_URL = f"rtsp://{USERNAME}:{PASSWORD}@{IP_ADDRESS}:{PORT}/stream1"
    LEARNER_PATH = '../NN.pkl' # Adjust learner path

    dbutils.DATABASE_PATH = '../database.csv'
    dbutils.VIDEOS_PATH = '../videos/'

    db = dbutils.Database(log=True)
    cam = Camera(RTSP_URL, db, log=True)
    event = threading.Event()
    print('Starting the camera')
    cam.start(event, 30, 4)
    print('Program ended')