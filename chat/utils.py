from twilio.rest import Client
import qrcode
from io import BytesIO
from django.core.files import File

def send_otp(mobile, otp):
    account_sid = "AC764f1b73362ebab73be5e7cba710bbc8"
    auth_token = "8bb8ffbb6ab867dc8683c41ec0474ec4"
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=f'Your OTP for Babel-on is: {otp}',
        from_='+12054988451',  # Your Twilio phone number
        to=mobile
    )

    print(message.sid)




def generate_qr_code(user):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    profile_url = f'http://localhost:8000/user/{user.username}'  # Adjust based on your URL pattern
    qr.add_data(profile_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    file_name = f'qr_code-{user.username}.png'
    user.qr_code.save(file_name, File(buffer), save=False)
