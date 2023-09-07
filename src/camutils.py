from fastai.vision.all import *
import cv2 as cv
import threading
import numpy as np
import dbutils
from datetime import datetime
import time

LEARNER_PATH = './NN.pkl'

# A classifier based on CNN that identifies object on a video/image
# Possible options: Empty; Human; Cat; Dog; Fox
class Classifier():
    def __init__(self):
        self.LEARNER_PATH = LEARNER_PATH
        self.learner = load_learner(self.LEARNER_PATH)
    
    # Classifies a video. Video must be a list of frames
    def classify_video(self, video):
        predictions = {'Empty': 0,
                       'Human': 0,
                       'Cat'  : 0,
                       'Dog'  : 0,
                       'Fox'  : 0}
        # Get predictions for each frame
        for frame in video:
            predictions[self.classify_img(frame)] += 1

        # Return 'Empty' if >90% of frames are classified as empty
        empty_count = predictions['Empty']
        predictions['Empty'] = 0
        if (empty_count / len(video) > 0.95):
            return 'Empty'
        
        # Else return most popular prediction
        else:
            return max(predictions)

    # Classifies a single image
    def classify_img(self, img):
        label = self.learner.predict(img)[0]
        return label


class Camera():
    def __init__(self, rtsp_url, database, log=False):
        self.rtsp_url = rtsp_url
        self.classifier = Classifier()
        self.database = database
        self.log = log

        # Number of pixels to crop each side
        self.top_crop = 100
        self.bottom_crop = 10
        self.left_crop = 0
        self.right_crop = 50

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
    
    # Crops frame by n pixels in each direction
    def crop_frame(self, frame, top_crop, bottom_crop, left_crop, right_crop):
        return frame[top_crop : frame.shape[0] - bottom_crop, 
                     left_crop : frame.shape[1] - right_crop]
    
    # Read 1 frame from a camera
    def read_frame(self):
        success, frame = self.cam.read()
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB) # Convert from BGR to RGB
        frame = self.crop_frame(frame, self.top_crop, self.bottom_crop, self.left_crop, self.right_crop) # Crop the frame
        return success, frame
    
    # Start looking for movement on the camera
    def start(self, end: threading.Event, mse_threshold, consequent_frames_threshold):
        ''' Starts looking for movement on a camera until stopped by main program
            or an error occurs. When MSE between <n> consequent frames exceeds threshold,
            the next 70 frames (~5 seconds) are recorded. When frames are finished recording,
            they are passed to Classifier which assigns a label. If the label is not empty, 
            mp4 file is created and saved, and the database is updated'''
        
        # Connect to the camera
        self.cam = cv.VideoCapture(self.rtsp_url)
        self.print_log(f"Connected to camera at {self.rtsp_url}")

        frames = []
        success, prev_frame = self.read_frame()
        consequent_frames = 0
        to_be_saved = 0

        # Keep reading new frames until either stopped by main program or error occurs
        while self.cam.isOpened() and not end.is_set() and success:
            # Read new frame
            success, new_frame = self.read_frame()

            # Update number of consequent frames which exceeded MSE threshold (or reset to 0)
            if self.mse(prev_frame, new_frame) > mse_threshold:
                consequent_frames += 1
            else:
                consequent_frames = 0

            # Queue 70 frames to be saved if enough consequent frames show movement
            if (consequent_frames > consequent_frames_threshold):
                self.print_log("Queueing 70 frames to be saved")
                to_be_saved = 70

            # Save the current frame if queued
            if to_be_saved > 0:
                to_be_saved -= 1
                frames.append(new_frame)

            # Process frames when they are finished recording
            elif len(frames) != 0:
                self.print_log("Finished recording frames, starting processing")
                self.process_frames(frames)
                frames = []

            prev_frame = new_frame

        self.cam.release()
        cv.destroyAllWindows()

    # Classifies a video with neural net 
    def process_frames(self, frames):
        # Get a prediction
        pred = self.classifier.classify_video(frames)
        self.print_log(f'Object labeled as {pred}')
        
        if pred == 'Empty':
            return
        
        absolute_time = int(time.time()) # Time in seconds since 1 January 1970
        formatted_time = time.strftime("%d/%m/%y %Hh:%Mm:%Ss") # Date in human-readable format
        file_name_time = time.strftime("%d-%m-%y %Hh %Mm %Ss") # Time for file name
        video_name = pred + " " + file_name_time
        db.write_record([absolute_time, formatted_time, pred])
        db.save_video(frames, video_name, self.fps)


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