from django.urls import path
from django.contrib import admin

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('admin_panel/', admin.site.urls, name="admin_panel"),
    path('stream/<int:stream_id>', views.stream, name='stream'),
    path('add_stream/', views.add_stream, name='add_stream'),
    path('add_clip/', views.add_clip, name='add_clip'),
    path('delete_stream/<str:user_name>/<str:stream_link>', views.delete_stream, name='delete_stream')
]
