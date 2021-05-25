#####################
# IMPORT LIBS
#####################

import flask
from flask import request
import subprocess
from twitch_stream_recorder import downloader_config
import os
from pathlib import Path
import time
import requests
import moviepy.editor
import uuid
import random
import time
import pandas as pd
import moviepy
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import numpy as np
from joblib import load

#####################
# IMPORT LOCAL FILES
#####################

from config import Config
from detector.detector import HighlightDetector

class StreamProcessor:
    '''
    Operates on top of the stream link
    Downloads, cuts and uploads stream
    Talks to the ML models
    '''

    def __init__(self, stream_link: str, user_name: str, stream_dataframe_name: str):
        self.stream_link = stream_link
        self.user_name = user_name
        self.stream_dataframe_name = stream_dataframe_name
        

        self.highlight_detector = HighlightDetector(self.stream_link, self.stream_dataframe_name)

        self.path_to_folder = Path(downloader_config.root_path) / 'recorded' / self.stream_link
        self.path_to_input_file = ''
        self.path_to_output_file = ''
        self.date_format = '%Y-%m-%d %H:%M:%S.%f'

    def download_stream(self):
        '''
        Starts background process of stream download
        Saves stream process, so it can be killed later
        '''

        cmd = f'nohup python3 {Config.twitch_download_app_path} --uid {self.stream_dataframe_name} --username {self.stream_link} --quality 480p --disable-ffmpeg &'
        download_process = subprocess.Popen([cmd], shell=True)

        return download_process

    def get_predictions(self) -> str:
        self.highlight_detector.start()

    def check_predictions(self, saved_prediction_indices) -> str:
        start_time, duration = None, None

        if not os.path.isfile(f'{self.stream_dataframe_name}_chat.csv'):
            return start_time, duration, saved_prediction_indices
        
        if not os.path.isfile(f'{self.stream_dataframe_name}_movement.csv'):
            return start_time, duration, saved_prediction_indices
    
        if not os.path.isfile(f'{self.stream_dataframe_name}_sound.csv'):
            return start_time, duration, saved_prediction_indices


        chat = pd.read_csv(f'{self.stream_dataframe_name}_chat.csv')
        movement = pd.read_csv(f'{self.stream_dataframe_name}_movement.csv')
        sound = pd.read_csv(f'{self.stream_dataframe_name}_sound.csv')

        data = pd.merge(chat, movement.drop(columns=['end_time']), on = 'start_time')
        data = pd.merge(data, sound.drop(columns=['end_time']), on = 'start_time')
        data.to_csv(f'{self.stream_dataframe_name}.csv', index = None)
        
        sc = load('standard_scaler.joblib')
        data.iloc[:, 2:] = sc.transform(data.iloc[:, 2:].values)

        X = data.iloc[:, 2:]
        model = load('model.joblib')
        probas = model.predict_proba(X)[:, 1]

        sorted_indices = np.argsort(probas)[::-1]

        best_index = -1
        for idx in sorted_indices:
            if (idx not in saved_prediction_indices) and (probas[idx] > 0.2):
                saved_prediction_indices.append(idx)
                best_index = idx
                break

        if best_index == -1:
            return start_time, duration, saved_prediction_indices

        for (index, row) in data.iterrows():
            if index == best_index:
                start_time = (datetime.strptime(row['start_time'], self.date_format) - datetime.strptime(data.loc[0, 'start_time'], self.date_format)).total_seconds()
                
                start_time = time.strftime('%H:%M:%S', time.gmtime(start_time)) + '.0'
                duration = time.strftime('%H:%M:%S', time.gmtime(10)) + '.0'
                break

        try:
            self.path_to_input_file = str(self.path_to_folder / f'{self.stream_dataframe_name}.mp4')
        except:
            start_time, duration = None, None


        return start_time, duration, saved_prediction_indices

    def extract_time_frame(self, time_start: str, video_duration: str):
        '''
        Based on the ML model output
        saves videoclip from time_start till time_end

        time_start: str - start of the stream clip fragment; format: 00:00:00.0
        video_duration: str - length of video; format: 00:00:00.0
        stream_name: str - name of the stream
        '''
        self.clip_name = str(uuid.uuid1())
        self.path_to_output_file = str(self.path_to_folder / f'{self.clip_name}.mp4')
        if os.path.isfile(self.path_to_input_file):
            cmd = f'ffmpeg -ss {time_start} -i "{self.path_to_input_file}" -c copy -t {video_duration} "{self.path_to_output_file}"'
            cut_process = subprocess.Popen([cmd], shell = True)

        return cut_process


    def save_clip_to_gs(self) -> str:
        '''
        Saves extracted video clip to google storage 
        '''
        gs_clip_name = self.path_to_output_file.split('/')[-1]
        gs_clip_path = f'gs://{Config.google_cloud_storage_bucket_name}/{gs_clip_name}'
        cmd = f'gsutil cp {self.path_to_output_file} {gs_clip_path}'
        save_process = subprocess.Popen([cmd], shell = True)        
        p_status = save_process.wait()

        try:
            os.remove(self.path_to_output_file) # delete current clip from the folder
        except:
            print('No clip found for deletion!')

        gs_public_clip_path = f'https://storage.googleapis.com/{Config.google_cloud_storage_bucket_name}/{gs_clip_name}'
        return gs_public_clip_path

    def process_killer(self):
        '''
        Tmp way out to kill all running processes related to video download
        '''
        cmd = f'pkill -f twitch_stream_recorder'
        cut_process = subprocess.Popen([cmd], shell = True)
        
        cmd = f'pkill -f streamlink'
        cut_process = subprocess.Popen([cmd], shell = True)


    def send_clip_to_webapp(self, gs_public_clip_path: str):
        '''
        Sends info about google storage clip to the webapp backend
        '''
        
        # api-endpoint
        URL = f'http://{Config.webapp_public_ip}:{Config.webapp_public_port}/add_clip'
        PARAMS = {'user_name': self.user_name, 'stream_link': self.stream_link, 'clip_link':gs_public_clip_path}
        try:
            requests.get(url = URL, params = PARAMS, timeout=1)
        except:
            pass

    @staticmethod
    def convert_time(seconds):
        '''
        Helper function to convert from seconds to hh:mm:ss values
        '''
        hours = seconds // 3600
        seconds %= 3600
        mins = seconds // 60
        seconds %= 60
        return hours, mins, seconds