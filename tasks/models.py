from django.db import models


class Task(models.Model):
    class Priority(models.TextChoices):
        HIGH = 'high', 'Haute'
        MEDIUM = 'medium', 'Moyenne'
        LOW = 'low', 'Basse'

    session_key = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_done', '-created_at']

    def __str__(self):
        return f'{self.title} ({self.get_priority_display()})'
