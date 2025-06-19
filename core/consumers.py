from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import Room, RoomSession
from django.contrib.auth.models import AnonymousUser

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.room_id = None

    async def disconnect(self, close_code):
        if self.room_id:
            await self.remove_session()

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'join':
            self.room_id = data.get('roomId')
            self.room_group_name = f'room_{self.room_id}'
            room = await self.get_room()
            if not room:
                await self.close()
                return
            # Убрана проверка allow_guests, теперь пускаем всех
            self.is_host = (self.scope.get('user') and not self.scope['user'].is_anonymous and room.host_id == self.scope['user'].id)
            self.allow_control = room.allow_control
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.add_session()
        elif data.get('type') == 'sync':
            room_id = data.get('roomId')
            action = data.get('action')
            room = await self.get_room_by_id(room_id)
            # allow_control: если False — только хост может отправлять sync
            is_host = (self.scope.get('user') and not self.scope['user'].is_anonymous and room and room.host_id == self.scope['user'].id)
            if room and (room.allow_control or is_host):
                room_group_name = f'room_{room_id}'
                await self.channel_layer.group_send(
                    room_group_name,
                    {
                        'type': 'sync_message',
                        'action': action,
                        'sender_channel': self.channel_name,
                    }
                )

    async def sync_message(self, event):
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'sync',
                'action': event['action'],
            }))

    @database_sync_to_async
    def add_session(self):
        # Не создавать комнату автоматически, только подключаться к существующей
        try:
            room = Room.objects.get(room_id=self.room_id)
        except Room.DoesNotExist:
            return  # Не добавлять сессию, если комнаты нет
        RoomSession.objects.get_or_create(room=room, session_key=self.channel_name)

    @database_sync_to_async
    def remove_session(self):
        RoomSession.objects.filter(room__room_id=self.room_id, session_key=self.channel_name).delete()
        # Если в комнате больше нет сессий — удалить комнату
        if not RoomSession.objects.filter(room__room_id=self.room_id).exists():
            Room.objects.filter(room_id=self.room_id).delete()

    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(room_id=self.room_id)
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def get_room_by_id(self, room_id):
        try:
            return Room.objects.get(room_id=room_id)
        except Room.DoesNotExist:
            return None
