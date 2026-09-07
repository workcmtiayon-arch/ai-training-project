from unittest.mock import patch

from django.test import TestCase

from .providers import ProviderToolResult
from .schemas import AssistantResponse
from .services import generate_assistant_reply, stream_assistant_reply
from .tools import execute_tool_call
from .schemas import ToolCall
from tasks.models import Task


class AssistantServiceTests(TestCase):
    @patch('ai_engine.services.GeminiProvider')
    def test_service_orchestrates_history_without_network(self, provider_class):
        provider_class.return_value.generate_reply.return_value = AssistantResponse(content='Réponse simulée')

        result = generate_assistant_reply([
            {'role': 'user', 'content': 'Bonjour'},
            {'role': 'assistant', 'content': 'Bonjour !'},
        ])

        self.assertEqual(result, 'Réponse simulée')
        provider_class.return_value.generate_reply.assert_called_once()
        history = provider_class.return_value.generate_reply.call_args.args[0]
        self.assertEqual(len(history), 2)

    def test_tool_cannot_update_task_from_another_session(self):
        task = Task.objects.create(session_key='owner-session', title='Privée', priority='high')

        result = execute_tool_call(
            ToolCall(name='update_task', arguments={'task_id': task.id, 'title': 'Intrusion'}),
            session_key='other-session',
        )

        task.refresh_from_db()
        self.assertIn('introuvable', result)
        self.assertEqual(task.title, 'Privée')

    def test_create_tool_persists_task_in_current_session(self):
        result = execute_tool_call(
            ToolCall(name='create_task', arguments={'title': 'Apprendre les tools', 'priority': 'medium'}),
            session_key='learning-session',
        )

        self.assertIn('Tâche créée', result)
        self.assertTrue(Task.objects.filter(session_key='learning-session', title='Apprendre les tools').exists())

    def test_analyze_tool_reports_only_current_session_tasks(self):
        Task.objects.create(session_key='analysis-session', title='Urgent', priority='high')
        Task.objects.create(session_key='analysis-session', title='Déjà fait', priority='low', is_done=True)
        Task.objects.create(session_key='other-session', title='Privée', priority='high')

        result = execute_tool_call(ToolCall(name='analyze_tasks', arguments={}), 'analysis-session')

        self.assertIn('2 tâche(s)', result)
        self.assertIn('commencez par Urgent', result)
        self.assertNotIn('Privée', result)

    @patch('ai_engine.services.GeminiProvider')
    def test_streaming_tool_action_returns_django_report_without_second_ai_call(self, provider_class):
        def initial_tool_stream(*args, **kwargs):
            if False:
                yield ''
            return ProviderToolResult(
                text='',
                calls=[ToolCall(name='create_task', arguments={'title': 'Action directe', 'priority': 'high'})],
            )

        provider_class.return_value.stream_with_tools.side_effect = initial_tool_stream

        chunks = list(stream_assistant_reply([{'role': 'user', 'content': 'Crée une tâche'}], 'stream-session'))

        self.assertIn('Tâche créée', ''.join(chunks))
        self.assertTrue(Task.objects.filter(session_key='stream-session', title='Action directe').exists())
        provider_class.return_value.stream_with_tool_results.assert_not_called()
