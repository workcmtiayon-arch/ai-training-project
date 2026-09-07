from django.db import transaction

from .models import Task


DEMO_SESSION_KEY = 'demo-seed-session'


def ensure_demo_tasks(session_key: str) -> None:
    """Copie les données de démonstration dans une session nouvellement créée.

    La vue marque ensuite la session comme initialisée ; les données ne sont
    donc jamais recréées après une suppression complète.
    """
    if Task.objects.filter(session_key=session_key).exists():
        return
    demo_tasks = Task.objects.filter(session_key=DEMO_SESSION_KEY)
    if not demo_tasks.exists():
        return
    with transaction.atomic():
        Task.objects.bulk_create([
            Task(
                session_key=session_key,
                title=task.title,
                description=task.description,
                priority=task.priority,
                is_done=task.is_done,
            )
            for task in demo_tasks
        ])


def serialize_task(task: Task) -> dict:
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'priority_label': task.get_priority_display(),
        'is_done': task.is_done,
        'created_at': task.created_at.isoformat(),
    }
