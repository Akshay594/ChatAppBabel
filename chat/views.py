from .models import CustomUser
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import send_otp, generate_qr_code
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer, PublicUserSerializer
from rest_framework.decorators import api_view, permission_classes
from .models import ConnectionRequest, CustomUser
from django.shortcuts import get_object_or_404

import unicodedata
from googletrans import Translator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


OTP_EXPIRATION_TIME = getattr(settings, 'OTP_EXPIRATION_TIME', 5)  # minutes

translator = Translator()

def remove_diacritics(text):
    if not text:
        return ''
    normalized_text = unicodedata.normalize('NFD', text)
    return ''.join(char for char in normalized_text if unicodedata.category(char) != 'Mn')

@require_http_methods(["POST"])
@csrf_exempt
def translate_text(request):
    try:
        data = json.loads(request.body)
        input_text = data.get('input_text')
        dest_language = data.get('dest', 'en')

        if not input_text:
            return JsonResponse({'error': 'Input text is empty'}, status=400)

        translation = translator.translate(input_text, dest=dest_language)

        if not translation:
            return JsonResponse({'error': 'Translation failed'}, status=500)

        translated_text = translation.text if translation.text else ''
        pronunciation = translation.pronunciation if translation.pronunciation else remove_diacritics(translated_text)

        return JsonResponse({
            'translated_text': translated_text,
            'pronunciation': pronunciation,
            'detected_language': translation.src
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_connection_request(request, receiver_id):
    receiver = get_object_or_404(CustomUser, id=receiver_id)
    ConnectionRequest.objects.create(sender=request.user, receiver=receiver)
    return Response({'message': 'Connection request sent'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_connection_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)
    connection_request.status = 'accepted'
    connection_request.save()
    return Response({'message': 'Connection request accepted'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_connection_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)
    connection_request.status = 'rejected'
    connection_request.save()
    return Response({'message': 'Connection request rejected'}, status=status.HTTP_200_OK)


def is_otp_valid(user, otp):
    if not user.otp_created:
        return False
    if (timezone.now() - user.otp_created).seconds > OTP_EXPIRATION_TIME * 60:
        return False
    return user.otp == otp

class RegisterView(APIView):
    def post(self, request):
        mobile = request.data.get('mobile')
        if not mobile:
            return Response({'error': 'Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = CustomUser.objects.get_or_create(mobile=mobile, defaults={'is_active': False})
        if created:
            user.otp = CustomUser.objects._generate_otp()
            user.otp_created = timezone.now()
            user.save()
            send_otp(mobile, user.otp)
            return Response({
                'message': f'OTP sent to the mobile number {mobile}',
                'status': True
                }, status=status.HTTP_200_OK)
        else:
            # Send OTP again if the user is not active yet
            if not user.is_active:
                user.otp = CustomUser.objects._generate_otp()
                user.otp_created = timezone.now()
                user.save()
                send_otp(mobile, user.otp)
                return Response({
                    'message': 'OTP resent, please verify to activate your account',
                    'status': True
                    }, status=status.HTTP_200_OK)
            return Response({'error': 'A user with this mobile number already exists'}, status=status.HTTP_409_CONFLICT)


class LoginView(APIView):
    def post(self, request):
        mobile = request.data.get('mobile')
        if not mobile:
            return Response({
                'error': 'Mobile number is required',
                'status': False
                }, status=status.HTTP_400_BAD_REQUEST)

        # user, created = CustomUser.objects.get_or_create(mobile=mobile)
        try:
            user = CustomUser.objects.get(mobile=mobile)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found. Please register your account first.',
                'status': False
                }, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP
        user.otp = CustomUser.objects._generate_otp()
        user.otp_created = timezone.now()
        user.save()
        send_otp(mobile, user.otp)
        return Response({
            'message': 'OTP sent to the mobile number',
            'status': True
            }, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    def post(self, request):
        mobile = request.data.get('mobile')
        otp = request.data.get('otp')
        if not mobile or not otp:
            return Response({'error': 'Mobile number and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(mobile=mobile).first()
        if user and is_otp_valid(user, otp):
            user.verify_otp(otp)  # Activate the user if OTP is valid

            # Generate JWT token for login
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'OTP verified successfully',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'status': True
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid OTP or OTP expired'}, status=status.HTTP_400_BAD_REQUEST)



class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class SetUsernameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Ensure the user is active (has verified OTP)
        if not user.is_active:
            return Response({'error': 'User must verify OTP before setting username'}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get('username')
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username=username).exists():
            return Response({'error': 'This username is already taken'}, status=status.HTTP_409_CONFLICT)

        user.username = username
        generate_qr_code(user)  # Generate QR code
        user.save()

        qr_code_url = request.build_absolute_uri(user.qr_code.url)
        # Clean the url to get the only image
        qr_code_url = qr_code_url.split('?')[0]


        refresh = RefreshToken.for_user(user)  # Generate JWT token for login

        return Response({
            'message': 'Username set and QR code generated',
            'qr_code_url': qr_code_url,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'status': True
        }, status=status.HTTP_201_CREATED)


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    

# Add a new view to show user profile while unauthenticated
    
class PublicUserView(APIView):
    def get(self, request, username):
        try:
            user = CustomUser.objects.get(username=username)
            serializer = PublicUserSerializer(user)
            qr_code_url = request.build_absolute_uri(user.qr_code.url)
            # Clean the url to get the only image
            qr_code_url = qr_code_url.split('?')[0]

            new_data = serializer.data
            new_data['qr_code_url'] = qr_code_url
            return Response({'user': new_data}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        