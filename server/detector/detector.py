import twitch
import pandas as pd

from config import Config
from .chat.chat import ChatDetector
from .movement.movement import MovementDetector
from .sound.sound import SoundDetector
from datetime import datetime
import time
from multiprocessing import Process
import threading

class HighlightDetector:

    def __init__(self, channel_name: str, stream_dataframe_name: str):
        self.channel_name = channel_name

        default_columns = ['start_time', 'end_time']
        chat_columns = ['message_counts', 'positive_message_count', 'negative_message_count']
        sound_columns = ['sound_loudness', 
                         'Music', 'Walk, footsteps', 'Speech', 
                         'Male speech, man speaking', 'Female speech, woman speaking', 'Child speech, kid speaking', 
                         'Fusillade', 'Gunshot, gunfire', 'Machine gun', 'Thunder', 'Thunderstorm', 'Artillery fire', 'Boom',
                         'Laughter', 'Baby laughter', 'Belly laugh'
                        ]
        movement_columns = ['movement_amount']

        self.chat_features = pd.DataFrame([], columns = default_columns + chat_columns)
        self.sound_features = pd.DataFrame([], columns = default_columns + sound_columns)
        self.movement_features = pd.DataFrame([], columns = default_columns + movement_columns)

        self.chat_detector = ChatDetector(self.channel_name, self.chat_features, stream_dataframe_name)
        self.sound_detector = SoundDetector(self.channel_name, self.sound_features, stream_dataframe_name)
        self.movement_detector = MovementDetector(self.channel_name, self.movement_features, stream_dataframe_name)


    def start(self):
        start_time = datetime.fromtimestamp(time.time())
        self.chat_detector.start(start_time)

        movement = threading.Thread(target=self.movement_detector.start, args=(start_time, ))
        movement.start()

        sound = threading.Thread(target=self.sound_detector.start, args=(start_time, ))
        sound.start()


if __name__ == '__main__':
    # for debugging purposes
    # HighlightDetector('rogue')
    pass
