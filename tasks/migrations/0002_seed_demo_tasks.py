from django.db import migrations


DEMO_SESSION_KEY = 'demo-seed-session'


def seed_demo_tasks(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    if Task.objects.filter(session_key=DEMO_SESSION_KEY).exists():
        return
    Task.objects.bulk_create([
        Task(session_key=DEMO_SESSION_KEY, title='TEST — Lire la documentation du projet', description='Découvrir le flux chat, tâches et tool calling.', priority='high'),
        Task(session_key=DEMO_SESSION_KEY, title='TEST — Réviser les bases Django', description='Modèles, vues, URLs et migrations.', priority='medium'),
        Task(session_key=DEMO_SESSION_KEY, title='TEST — Tester une action IA', description='Demander à l’assistant de créer une tâche.', priority='high'),
        Task(session_key=DEMO_SESSION_KEY, title='TEST — Nettoyer les notes', description='Classer les prochaines idées d’apprentissage.', priority='low'),
        Task(session_key=DEMO_SESSION_KEY, title='TEST — Valider l’interface', description='Vérifier le responsive du panneau de tâches.', priority='medium', is_done=True),
    ])


def remove_demo_tasks(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    Task.objects.filter(session_key=DEMO_SESSION_KEY).delete()


class Migration(migrations.Migration):
    dependencies = [('tasks', '0001_initial')]
    operations = [migrations.RunPython(seed_demo_tasks, remove_demo_tasks)]
