import json
import aiohttp
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs

class ChatConsumer(AsyncWebsocketConsumer):
    # A class variable to keep track of user languages
    user_languages = {}

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Extract language from query parameters
        query_string = self.scope['query_string'].decode()
        self.preferred_language = parse_qs(query_string).get('lang', ['en'])[0]

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Store user language preference
        self.user_languages[self.channel_name] = self.preferred_language

        await self.accept()

    async def disconnect(self, close_code):
        # Remove user language preference
        if self.channel_name in self.user_languages:
            del self.user_languages[self.channel_name]

        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # async def translate_message(self, message, dest_language):
    #     async with aiohttp.ClientSession() as session:
    #         payload = {"input_text": message, "dest": dest_language}
    #         async with session.post('https://4452ufm5bl.execute-api.us-west-2.amazonaws.com/dev/translate/', json=payload) as response:
    #             response_data = await response.json()
    #             print(response_data)
    #             # Check for pronunciation, else fall back to translated text
    #             pronunciation = response_data.get("pronunciation")
    #             if pronunciation:
    #                 return pronunciation
    #             else:
    #                 return response_data.get("translated_text", message)

    async def translate_message(self, message, dest_language):
        async with aiohttp.ClientSession() as session:
            # Prepare the payload with the expected keys
            payload = {"input_text": message, "dest": dest_language}
            
            # Assuming the Django server is running on localhost and port 8000
            # Change the URL to match your setup
            url = 'http://localhost:8000/chat/api/translate/'
            
            async with session.post(url, json=payload) as response:
                # Check if the response status is 200 OK before proceeding
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Check for pronunciation, else fall back to translated text
                    pronunciation = response_data.get("pronunciation")
                    if pronunciation:
                        return pronunciation
                    else:
                        return response_data.get("translated_text", message)
                else:
                    # Handle error or unexpected response
                    print(f"Error: {response.status}")
                    return message  # Fall back to the original message if the translation fails


    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group without translating here
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat.message", "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Translate the message to the user's preferred language
        user_language = self.user_languages.get(self.channel_name, 'en')
        translated_message = await self.translate_message(message, user_language)

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": translated_message}))
