from django.db import models


class Conversation(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=120, default='Nouvelle conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} ({self.session_key})'


class Message(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'Utilisateur'
        ASSISTANT = 'assistant', 'Assistant'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.role}: {self.content[:40]}'
