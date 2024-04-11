from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from chat.urls import chat_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include((chat_urls, 'chat'), namespace='chat')),
 
]
