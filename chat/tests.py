import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import Message


class ChatViewTests(TestCase):
    def test_chat_page_is_available_and_session_based(self):
        response = self.client.get(reverse('chat_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Votre assistant IA')

    @patch('chat.views.stream_assistant_reply', return_value=iter(['Réponse progressive']))
    def test_message_endpoint_streams_and_persists_assistant_reply(self, stream_reply):
        self.client.get(reverse('chat_page'))
        response = self.client.post(
            reverse('send_message'),
            data=json.dumps({'message': 'Bonjour'}),
            content_type='application/json',
        )

        body = b''.join(response.streaming_content).decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Réponse progressive', body)
        self.assertIn('"type": "done"', body)
        self.assertTrue(Message.objects.filter(role=Message.Role.ASSISTANT, content='Réponse progressive').exists())
