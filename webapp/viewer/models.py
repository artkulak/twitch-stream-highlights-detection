from django.db import models

class User(models.Model):
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200)

class Stream(models.Model):
    stream_link = models.CharField(max_length=200) # streamer page name
    stream_name = models.CharField(max_length=200) # stream name
    user_id = models.CharField(max_length=200) # user id

class StreamHighlight(models.Model):
    user_id = models.CharField(max_length=200) # user id
    stream_link = models.CharField(max_length=200) # streamer page name
    clip_link = models.CharField(max_length=500) # link to stream

    


