import twitch
import os
import sys; sys.path.append(os.path.abspath('.'))
from config import Config
import time
from datetime import datetime, timedelta
from transformers import pipeline
import pandas as pd

class ChatDetector:

    def __init__(self, channel_name, stream_features, stream_dataframe_name):
        self.classifier = pipeline('sentiment-analysis')
        self.channel_name = channel_name
        self.stream_dataframe_name = stream_dataframe_name

        self.stream_features = stream_features
        self.seconds = 10

    def process(self, start_time, message_sentiment):

        i = self.stream_features.shape[0]
        message_time = datetime.fromtimestamp(time.time())

        if i == 0:
            message_time = start_time

        try:
            min_time = self.stream_features.loc[i-1, 'start_time']
            max_time = self.stream_features.loc[i-1, 'end_time']
        except:
            min_time, max_time = None, None
    
        if max_time != None and message_time >= min_time and message_time <= max_time:
            self.stream_features.loc[i-1, 'message_counts'] += 1
            if message_sentiment[0]['label'] == 'NEGATIVE':
                self.stream_features.loc[i-1, 'negative_message_count'] += 1
            if message_sentiment[0]['label'] == 'POSITIVE':
                self.stream_features.loc[i-1, 'positive_message_count'] += 1
        else:
            self.stream_features.loc[i] = [start_time + timedelta(seconds = self.seconds * i), start_time + timedelta(seconds = self.seconds * (i+1)), 0, 0, 0]
            self.stream_features.loc[i, 'message_counts'] += 1
            if message_sentiment[0]['label'] == 'NEGATIVE':
                self.stream_features.loc[i, 'negative_message_count'] += 1
            if message_sentiment[0]['label'] == 'POSITIVE':
                self.stream_features.loc[i, 'positive_message_count'] += 1
        
        self.stream_features.to_csv(f'{self.stream_dataframe_name}_chat.csv',  index = None) # change later to uid


    def start(self, start_time):
        # Twitch Chat
        chat = twitch.Chat(channel=self.channel_name, nickname=Config.nickname, oauth=Config.oauth_token)
        chat.subscribe(lambda message: self.process(start_time, self.classifier(message.text)))

if __name__ == '__main__':
    # for debug
    # chat = LiveChat('rogue')
    pass