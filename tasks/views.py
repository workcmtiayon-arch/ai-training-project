import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from pydantic import ValidationError

from ai_engine.schemas import CreateTaskArguments, UpdateTaskArguments

from .models import Task
from .services import ensure_demo_tasks, serialize_task


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _json_body(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


@require_GET
def task_list(request):
    session_key = _session_key(request)
    if not request.session.get('demo_tasks_seeded', False):
        ensure_demo_tasks(session_key)
        request.session['demo_tasks_seeded'] = True
    tasks = Task.objects.filter(session_key=session_key)
    return JsonResponse({'tasks': [serialize_task(task) for task in tasks]})


@require_POST
def task_create(request):
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({'error': 'Requête JSON invalide.'}, status=400)
    try:
        data = CreateTaskArguments.model_validate(payload)
    except ValidationError as exc:
        return JsonResponse({'error': exc.errors()[0]['msg']}, status=400)
    task = Task.objects.create(session_key=_session_key(request), **data.model_dump())
    return JsonResponse({'task': serialize_task(task)}, status=201)


@require_POST
def task_update(request, task_id):
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({'error': 'Requête JSON invalide.'}, status=400)
    try:
        data = UpdateTaskArguments.model_validate({'task_id': task_id, **payload})
    except ValidationError as exc:
        return JsonResponse({'error': exc.errors()[0]['msg']}, status=400)
    task = Task.objects.filter(id=task_id, session_key=_session_key(request)).first()
    if task is None:
        return JsonResponse({'error': 'Tâche introuvable.'}, status=404)
    changes = data.model_dump(exclude={'task_id'}, exclude_unset=True)
    for field, value in changes.items():
        setattr(task, field, value)
    task.save(update_fields=list(changes))
    return JsonResponse({'task': serialize_task(task)})


@require_POST
def task_delete(request, task_id):
    task = Task.objects.filter(id=task_id, session_key=_session_key(request)).first()
    if task is None:
        return JsonResponse({'error': 'Tâche introuvable.'}, status=404)
    task.delete()
    return JsonResponse({'deleted': task_id})
