from django.test import TestCase

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountFlowTests(TestCase):
    def test_authentication_pages_are_available(self):
        self.assertEqual(self.client.get(reverse('accounts:login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:signup')).status_code, 200)

    def test_signup_creates_hashed_user_and_logs_in(self):
        response = self.client.post(
            reverse('accounts:signup'),
            data={
                'username': 'alice',
                'email': 'ALICE@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )

        self.assertRedirects(response, reverse('chat_page'))
        user = User.objects.get(username='alice')
        self.assertEqual(user.email, 'alice@example.com')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username='first', email='person@example.com', password='StrongPass123!')

        response = self.client.post(
            reverse('accounts:signup'),
            data={
                'username': 'second',
                'email': 'PERSON@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'déjà utilisée')
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse('accounts:signup'),
            data={
                'username': 'alice',
                'email': 'alice@example.com',
                'password1': 'password',
                'password2': 'password',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'trop courant')
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_login_and_logout(self):
        User.objects.create_user(username='alice', password='StrongPass123!')

        response = self.client.post(reverse('accounts:login'), {'username': 'alice', 'password': 'StrongPass123!'})
        self.assertRedirects(response, reverse('chat_page'))
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_private_pages_redirect_anonymous_users(self):
        self.assertRedirects(self.client.get(reverse('chat_page')), '/comptes/connexion/?next=/')
