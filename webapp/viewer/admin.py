from django.contrib import admin

# Register your models here.

from .models import Stream, StreamHighlight

admin.site.register(Stream)
admin.site.register(StreamHighlight)