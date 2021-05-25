from keras import applications
import efficientnet.keras as efn
from keras import callbacks
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
import argparse
import numpy as np
from pathlib import Path
import cv2
from time import time
from time import sleep
import pandas as pd
from datetime import datetime, timedelta
import os
import cv2
import subprocess
import numpy as np


import cv2, queue, threading

class Config:
    '''
    Stores config variables for running movement predictor
    '''

    MODEL_PATH = 'detector/movement/effnet.h5' # path to effnet model weight file
    SKIP_MINUTES = 0 # how minutes to skip for prediction
    VIDEO_FPS = 30 # fps for a given video
    USE_FRAME = 30 # frequency of frames to use for prediction (e.g use every 30th frame to calc optical flow)
    ARR_MEMORY = 30 # how many predictions to remember for taking average
    ACCEPT_PAUSE = 30 # pause length higher than that is considered as a pause
    THRESHOLD = 0.4 # model prediction threshold

class Pipeline:

    '''
    Stores code for loading and inferencing effnet model
    '''
    
    def __init__(self, weightsPath):
        self.weightsPath = weightsPath

    def loadModel(self):
        '''
        Loads CNN model with pretrained weights
        '''
        efficient_net = efn.EfficientNetB1(
                weights='imagenet',
                input_shape=(32,32,3),
                include_top=False,
                pooling='max'
        )

        model = Sequential()
        model.add(efficient_net)
        model.add(Dense(units = 120, activation='relu'))
        model.add(Dense(units = 120, activation = 'relu'))
        model.add(Dense(units = 1, activation='sigmoid'))

        model.compile(optimizer=Adam(lr=1e-3), loss='binary_crossentropy', metrics=['accuracy'])
        model.load_weights(self.weightsPath)
        return model

    def getOptFlow(self, frame1, frame2, hsv):
        '''
        Calculates optical flow for 2 consequent frames
        '''

        flow = cv2.calcOpticalFlowFarneback(frame1,frame2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1])
        hsv[...,0] = ang*180/np.pi/2
        hsv[...,2] = cv2.normalize(mag,None,0,255,cv2.NORM_MINMAX)
        optflow = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
        optflow = cv2.resize(optflow, (32, 32)) / 255.0
        return optflow.reshape(1, 32, 32, 3), hsv

class MovementDetector:

    def __init__(self, channel_name: str, stream_features: str, stream_dataframe_name: str):

        self.pipeline = Pipeline(Config.MODEL_PATH)
        self.classifier = self.pipeline.loadModel()

        self.channel_name = channel_name
        self.stream_dataframe_name = stream_dataframe_name

        self.stream_features = stream_features
        self.seconds = 10

        self.stream_video_link = ''


    def process(self, frame, prev_frame, start_time, hsv):

        try:
            cv2.imwrite('frame.png', frame)
        except:
            pass

        i = self.stream_features.shape[0]
        message_time = datetime.fromtimestamp(time())

        if i == 0:
            message_time = start_time

        try:
            min_time = self.stream_features.loc[i-1, 'start_time']
            max_time = self.stream_features.loc[i-1, 'end_time']
        except:
            min_time, max_time = None, None
        if max_time != None and message_time >= min_time and message_time <= max_time:
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            prev_frame = cv2.cvtColor(prev_frame,cv2.COLOR_BGR2GRAY)
            optflow, hsv = self.pipeline.getOptFlow(prev_frame, frame, hsv)
            self.stream_features.loc[i-1, 'movement_amount'] += self.classifier.predict(optflow)[0][0]
        else:
            self.stream_features.loc[i] = [start_time + timedelta(seconds = self.seconds * i), start_time + timedelta(seconds = self.seconds * (i+1)), 0]
            
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            prev_frame = cv2.cvtColor(prev_frame,cv2.COLOR_BGR2GRAY)
            optflow, hsv = self.pipeline.getOptFlow(prev_frame, frame, hsv)
        
            self.stream_features.loc[i, 'movement_amount'] += self.classifier.predict(optflow)[0][0]
        
        self.stream_features.to_csv(f'{self.stream_dataframe_name}_movement.csv',  index = None) # change later to uid
        return hsv

    def start(self, start_time):
    
        video_path = f'../../streams/recorded/{self.channel_name}/{self.stream_dataframe_name}.mp4'
        short_video_path = f'../../streams/recorded/{self.channel_name}/{self.stream_dataframe_name}_short.mp4'
        prev_frame = None




        tot = 0
        while True:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)      # OpenCV2 version 2 used "CV_CAP_PROP_FPS"
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if fps < 1:
                continue
            
            dur = int(frame_count/fps)
            cap.release()

            
            subprocess.call(
                    ["ffmpeg", 
                    "-ss", f"{dur-4}",
                    "-i", f"{video_path}",
                    "-t", "1",
                    "-c", "copy",
                    f"{short_video_path}",
                    "-y",
                    # "-vcodec", "libx264"
                     ])

            cap = cv2.VideoCapture(short_video_path)
            _, frame = cap.read()
            cap.release()
            
            if frame is not None:
                if tot == 0:
                    hsv = np.zeros_like(frame)
                    hsv[...,1] = 255
                    prev_frame = frame


                hsv = self.process(frame, prev_frame, start_time, hsv)
                prev_frame = frame
                
                tot += 1
            
            sleep(1)