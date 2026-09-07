from typing import Type

from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

from tasks.models import Task
from tasks.services import serialize_task

from .schemas import (
    AnalyzeTasksArguments,
    CreateTaskArguments,
    DeleteTaskArguments,
    ListTasksArguments,
    ToolCall,
    UpdateTaskArguments,
)


TOOL_ARGUMENT_SCHEMAS: dict[str, Type[BaseModel]] = {
    'create_task': CreateTaskArguments,
    'list_tasks': ListTasksArguments,
    'update_task': UpdateTaskArguments,
    'delete_task': DeleteTaskArguments,
    'analyze_tasks': AnalyzeTasksArguments,
}

TOOL_DESCRIPTIONS = {
    'create_task': 'Créer une tâche dans la session courante.',
    'list_tasks': 'Lister les tâches de la session courante, éventuellement uniquement celles non terminées.',
    'update_task': 'Modifier une tâche appartenant à la session courante.',
    'delete_task': 'Supprimer une tâche appartenant à la session courante.',
    'analyze_tasks': 'Analyser les tâches de la session courante et proposer des conseils de priorisation.',
}


def gemini_tool_declarations() -> list[genai_types.FunctionDeclaration]:
    return [
        genai_types.FunctionDeclaration(
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            parametersJsonSchema=schema.model_json_schema(),
        )
        for name, schema in TOOL_ARGUMENT_SCHEMAS.items()
    ]


def _owned_task(task_id: int, session_key: str) -> Task | None:
    return Task.objects.filter(id=task_id, session_key=session_key).first()


def execute_tool_call(call: ToolCall, session_key: str) -> str:
    """Valide puis exécute un outil dans le périmètre de la session courante."""
    schema = TOOL_ARGUMENT_SCHEMAS.get(call.name)
    if schema is None:
        return f"Outil inconnu : {call.name}. Aucune opération exécutée."
    try:
        arguments = schema.model_validate(call.arguments)
    except ValidationError as exc:
        return f"Arguments invalides pour {call.name} : {exc.errors()[0]['msg']}. Aucune opération exécutée."

    if isinstance(arguments, CreateTaskArguments):
        task = Task.objects.create(session_key=session_key, **arguments.model_dump())
        return f"Tâche créée : « {task.title} », priorité {task.get_priority_display().lower()} (id {task.id})."

    if isinstance(arguments, ListTasksArguments):
        queryset = Task.objects.filter(session_key=session_key)
        if arguments.only_pending:
            queryset = queryset.filter(is_done=False)
        tasks = list(queryset[:20])
        if not tasks:
            return 'Aucune tâche ne correspond à la demande.'
        status = ', '.join(f'#{task.id} {task.title} ({task.get_priority_display().lower()})' for task in tasks)
        return f'{len(tasks)} tâche(s) trouvée(s) : {status}.'

    if isinstance(arguments, UpdateTaskArguments):
        task = _owned_task(arguments.task_id, session_key)
        if task is None:
            return 'Tâche introuvable dans la session courante. Aucune opération exécutée.'
        changes = arguments.model_dump(exclude={'task_id'}, exclude_unset=True)
        for field, value in changes.items():
            setattr(task, field, value)
        task.save(update_fields=[*changes.keys()])
        return f"Tâche « {task.title} » mise à jour ({', '.join(changes)})."

    if isinstance(arguments, DeleteTaskArguments):
        task = _owned_task(arguments.task_id, session_key)
        if task is None:
            return 'Tâche introuvable dans la session courante. Aucune opération exécutée.'
        title = task.title
        task.delete()
        return f"Tâche « {title} » supprimée."

    if isinstance(arguments, AnalyzeTasksArguments):
        tasks = list(Task.objects.filter(session_key=session_key))
        if not tasks:
            return 'Aucune tâche à analyser. Créez d’abord une tâche.'
        pending = [task for task in tasks if not task.is_done]
        high = [task for task in pending if task.priority == Task.Priority.HIGH]
        done = len(tasks) - len(pending)
        advice = []
        if high:
            advice.append(f'commencez par {high[0].title}')
        if len(pending) > 3:
            advice.append('découpez les tâches restantes en petites étapes')
        if done:
            advice.append(f'conservez le rythme : {done} tâche(s) terminée(s)')
        return f"Analyse : {len(tasks)} tâche(s), {len(pending)} en attente. Conseils : " + (' ; '.join(advice) or 'maintenez votre plan actuel') + '.'

    return 'Aucune opération exécutée.'
