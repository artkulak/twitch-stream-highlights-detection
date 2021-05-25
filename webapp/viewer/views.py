from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse


####################
# IMPORT OTHER LIBS
####################
import os
import numpy as np
import glob
import pandas as pd
from pathlib import Path
import shutil
import twitch
import requests

from .models import Stream, StreamHighlight
from .config import Config

class UserData:

    user = None


heatmap_points = []
def index(request):
    '''
    Renders login + main page
    '''
    global user

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            # if user is authentificated
            data = Stream.objects.all().filter(user_id=username)
            response_data = {
                "stream_data": data,
                "name" : username,
                "is_staff": user.is_staff,
            }
            return render(request, 'main.html', response_data)
        return render(request, 'index.html')
    elif not request.user.is_anonymous:
        username = request.user
        data = Stream.objects.all().filter(user_id=username)
        response_data = {
            "stream_data": data,
            "name" : username,
            "is_staff": request.user.is_staff,
        }
        return render(request, 'main.html', response_data)
    else:
        form = UserCreationForm()
    
    return render(request, 'index.html', {'form': form})

def add_stream(request):
    '''
    1. Add stream name + link to the database 
    2. Send stream link to the server for processing
    '''
    helix = twitch.Helix(Config.client_id, Config.secret_id)
    stream_link = request.POST['stream_link']

    # TODO: check if stream exists
    for user_id, videos in helix.users([stream_link]).videos(first=1):
        for video in videos:
                stream_name = video
    # add new stream to database           
    Stream.objects.create(stream_link = stream_link, stream_name = stream_name, user_id = request.user.username)

    data = Stream.objects.all()
    response_data = {
        "stream_data": data,
        "name" : request.user.username,
        "is_staff": request.user.is_staff,
    }

  
    # api-endpoint
    URL = f'http://{Config.server_ip}:{Config.server_port}/process_stream'
    PARAMS = {'stream_link':stream_link, 'user_name': request.user.username}

    try:
        requests.get(url = URL, params = PARAMS, timeout = 1)
    except:
        pass

    return redirect('/')


def add_clip(request):
    '''
    Processes incoming request from the ML server 
    Adds incoming highlight link to the database
    '''
    user_name = request.GET['user_name']
    stream_link = request.GET['stream_link']
    clip_link = request.GET['clip_link']

    print(user_name, stream_link, clip_link)
    # add new clip to database           
    StreamHighlight.objects.create(clip_link = clip_link, stream_link = stream_link, user_id = user_name)

    return redirect('/')

def stream(request, stream_id):
    '''
    Renders video page
    '''

    global stream
    stream = list(Stream.objects.all())[stream_id-1]
    clips_data = StreamHighlight.objects.all().filter(user_id=request.user.username, stream_link=stream.stream_link)


    response_data = {
                "name" : request.user.username,
                "stream_name": stream.stream_name,
                "stream_link": stream.stream_link,
                "is_staff": request.user.is_staff,
                "clips_data": clips_data
            }
    
    return render(request, 'stream.html', response_data)

def delete_stream(request, user_name, stream_link):

    Stream.objects.filter(stream_link=stream_link, user_id = user_name).delete()
    StreamHighlight.objects.filter(stream_link=stream_link, user_id = user_name).delete()

    return redirect('/')