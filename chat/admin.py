from django.contrib import admin
from .models import ChatMessage, CustomUser

admin.site.register(ChatMessage)
admin.site.register(CustomUser)