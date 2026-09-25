import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Task


class TaskCrudTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='StrongPass123!')
        self.client.force_login(self.user)

    def test_list_clones_demo_tasks_into_current_session(self):
        response = self.client.get(reverse('task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['tasks']), 5)

    def test_crud_is_session_scoped(self):
        self.client.get(reverse('task_list'))
        session_key = self.client.session.session_key
        task = Task.objects.create(session_key=session_key, title='À faire', priority='low')

        response = self.client.post(
            reverse('task_update', args=[task.id]),
            data=json.dumps({'is_done': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.is_done)

        response = self.client.post(reverse('task_delete', args=[task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=task.id).exists())

    def test_all_demo_tasks_can_be_deleted_permanently(self):
        response = self.client.get(reverse('task_list'))
        self.assertEqual(len(response.json()['tasks']), 5)
        session_key = self.client.session.session_key
        Task.objects.filter(session_key=session_key).delete()

        response = self.client.get(reverse('task_list'))

        self.assertEqual(response.json()['tasks'], [])

    def test_manual_task_is_saved_in_the_current_session(self):
        self.client.get(reverse('task_list'))
        response = self.client.post(
            reverse('task_create'),
            data=json.dumps({'title': 'Ma vraie tâche', 'description': 'Persistante', 'priority': 'high'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        session_key = self.client.session.session_key
        task = Task.objects.get(title='Ma vraie tâche')
        self.assertEqual(task.session_key, session_key)
        self.assertEqual(task.priority, Task.Priority.HIGH)
