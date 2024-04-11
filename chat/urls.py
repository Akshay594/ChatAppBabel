from django.urls import path
from .views import (RegisterView, 
                    VerifyOTPView, 
                    LoginView, 
                    LogoutView,
                    SetUsernameView, 
                    UserView, 
                    PublicUserView,
                    translate_text)

chat_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('set-username/', SetUsernameView.as_view(), name='set-username'),
    path('user/', UserView.as_view(), name='user'),
    path('user/<str:username>/', PublicUserView.as_view(), name='public-user'),
    path('translate/', translate_text, name='translate_text'),
]
