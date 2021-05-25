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
from multiprocessing import Process, Queue
import uuid

import os
os.environ["TOKENIZERS_PARALLELISM"] = "true"


#####################
# IMPORT LOCAL FILES
#####################

from processor import StreamProcessor
from detector.detector import HighlightDetector
from config import Config

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/process_stream', methods=['GET'])
def process_stream():
    saved_prediction_indices = []
    stream_link = request.args.get('stream_link')
    user_name = request.args.get('user_name')

    stream_uid = str(uuid.uuid1())
    FILE_PATH = f'../../streams/recorded/{stream_link}/{stream_uid}.mp4'

    stream_processor = StreamProcessor(stream_link, user_name, stream_uid)


    # start stream download on the background
    download_process = stream_processor.download_stream()

    print(f'Working for user: {user_name} and stream {stream_link}')

    print(download_process.pid) # for debug purposes
    while not os.path.isfile(FILE_PATH):
        pass

    p = Process(target=stream_processor.get_predictions(), args=())
    p.start()

    # wait for the new ML model predictions
    while True:
        
        # run models here

        time_start, duration, saved_prediction_indices = stream_processor.check_predictions(saved_prediction_indices) # once models return start/end time they will be available here

        if time_start is not None:
            cut_process = stream_processor.extract_time_frame(time_start, duration)
            gs_public_clip_path = stream_processor.save_clip_to_gs()
            stream_processor.send_clip_to_webapp(gs_public_clip_path)
            print('Clip added to google storage!')

        time.sleep(30)
    
    os.remove(f'{stream_uid}.csv')
    # tmp solution to kill all processes, doesn't work for multi user case
    stream_processor.process_killer()
    cut_process.terminate()
    download_process.terminate()    
    return ''
app.run(host='0.0.0.0', port=5555)
# app.run(port=5555)
