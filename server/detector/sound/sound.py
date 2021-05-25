import argparse
import numpy as np
from pathlib import Path
from time import time
from time import sleep
import pandas as pd
from datetime import datetime, timedelta
import os
import cv2
import subprocess
import librosa
import panns_inference
from panns_inference import AudioTagging, SoundEventDetection, labels

class SoundDetector:

    def __init__(self, channel_name: str, stream_features: str, stream_dataframe_name: str):

        self.channel_name = channel_name
        self.stream_dataframe_name = stream_dataframe_name

        self.stream_features = stream_features
        self.seconds = 10

        self.stream_video_link = ''

    def process(self, max_sound, labels, start_time):

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
            for column_name in self.stream_features.columns[3:]:
                self.stream_features.loc[i-1, column_name] += labels.query('display_name == @column_name')['prediction'].iloc[0]
        
            self.stream_features.loc[i-1, 'sound_loudness'] += max_sound
        else:
            self.stream_features.loc[i] = [start_time + timedelta(seconds = self.seconds * i), start_time + timedelta(seconds = self.seconds * (i+1)), 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

            for column_name in self.stream_features.columns[3:]:
                self.stream_features.loc[i, column_name] += labels.query('display_name == @column_name')['prediction'].iloc[0]
        
            self.stream_features.loc[i, 'sound_loudness'] += max_sound

        self.stream_features.to_csv(f'{self.stream_dataframe_name}_sound.csv',  index = None) # change later to uid

    def start(self, start_time):
        video_path = f'../../streams/recorded/{self.channel_name}/{self.stream_dataframe_name}.mp4'
        sound_path = f'../../streams/recorded/{self.channel_name}/{self.stream_dataframe_name}_sound.mp3'


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
                    "-i", f"{video_path}",
                    "-ss", f"{dur-5}",
                    "-t", "3",
                    "-map", "0:a",
                    # "-c", "copy",
                    f"{sound_path}",
                    "-y",
                    ])

            try:
                (sound, _) = librosa.load(sound_path, sr=32000, mono=True)
                max_sound = np.max(sound)

                # audio tagging
                sound = sound[None, :]  # (batch_size, segment_samples)
                at = AudioTagging()
                (clipwise_output, embedding) = at.inference(sound)
                
                labels = pd.read_csv('../../panns_data/class_labels_indices.csv')
                labels['prediction'] = clipwise_output.reshape(-1)
                # labels = labels.sort_values(by = 'prediction', ascending = False)


                self.process(max_sound, labels, start_time)
            except:
                pass


            
            sleep(1)
