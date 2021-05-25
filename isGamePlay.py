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
import pandas as pd
import datetime


# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


class Config:
    MODEL_PATH = 'effnet.h5' # path to effnet model weight file
    SKIP_MINUTES = 0 # how minutes to skip for prediction
    VIDEO_FPS = 30 # fps for a given video
    USE_FRAME = 30 # frequency of frames to use for prediction (e.g use every 30th frame to calc optical flow)
    ARR_MEMORY = 30 # how many predictions to remember for taking average
    ACCEPT_PAUSE = 30 # pause length higher than that is considered as a pause
    THRESHOLD = 0.4 # model prediction threshold

class Pipeline:
    
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
        return optflow.reshape(1, 32, 32, 3)


def run():
    # create pipeline
    output = []
    pipeline = Pipeline(Config.MODEL_PATH)
    model = pipeline.loadModel()
    
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', type=str, help='path to video file')
    args = parser.parse_args()
    inputPath = args.i
    outputName = inputPath.split('/')[-1].split('.')[0] + '.csv'
    tmpOutputName = 'output_' + inputPath.split('/')[-1].split('.')[0] + '.csv'
    
    # start cv2 video capture
    cap = cv2.VideoCapture(inputPath)
    totalFrames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = cap.get(cv2.CAP_PROP_POS_MSEC)

    ret, frame1 = cap.read()
    prvs = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
    hsv = np.zeros_like(frame1)
    hsv[...,1] = 255
    tot = 0
    preds = list(np.zeros(Config.ARR_MEMORY))


    while True:
        ret, frame2 = cap.read()

        # when there are no frames break loop
        try:
            next = cv2.cvtColor(frame2,cv2.COLOR_BGR2GRAY)
        except:
            break


        if tot > Config.VIDEO_FPS * 60 * Config.SKIP_MINUTES:
            if tot % Config.USE_FRAME == 0:
                optflow = pipeline.getOptFlow(prvs, next, hsv)
                pred = model.predict(optflow)
                
                # add new prediction to the memory
                preds.append(pred[0][0])
                preds.pop(0)

                # the resulting frame is considered 0 or 1 based on Config.ARR_MEMORY predictions
                output.append([tot / Config.USE_FRAME, np.mean(preds)])

                tmpDF = pd.DataFrame(output)
                tmpDF.columns = ['Seconds', 'Prediction']
                tmpDF.to_csv(tmpOutputName, index = None)

                printProgressBar(tot, totalFrames, prefix = 'Progress:', suffix = 'Complete', length = 100)
                # cv2.imshow('rgb', frame2)
                k = cv2.waitKey(1) & 0xff
            prvs = next
        tot += 1
    k = cv2.waitKey(1) & 0xff
    cap.release()



if __name__ == '__main__':
    run()