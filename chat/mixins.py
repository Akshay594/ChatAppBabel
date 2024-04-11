import os
from twilio.rest import Client


account_sid = "AC764f1b73362ebab73be5e7cba710bbc8"
auth_token = "8bb8ffbb6ab867dc8683c41ec0474ec4"

# account_sid = os.environ['TWILIO_ACCOUNT_SID']
# auth_token = os.environ['TWILIO_AUTH_TOKEN']

client = Client(account_sid, auth_token)

message = client.messages \
    .create(
         body='Your OTP for Babel-on: 1234',
         from_='+12054988451',
         to='+919509289876'
     )

print(message.sid)