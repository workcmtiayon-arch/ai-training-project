import json

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from ai_engine.exceptions import AIProviderError, AIServiceError
from ai_engine.services import stream_assistant_reply

from .models import Conversation, Message


def _get_conversation(request):
    if not request.session.session_key:
        request.session.create()
    conversation, _ = Conversation.objects.get_or_create(session_key=request.session.session_key)
    return conversation


@require_GET
def chat_page(request):
    conversation = _get_conversation(request)
    messages = conversation.messages.all()
    return render(request, 'chat/chat.html', {'messages': messages})


@require_POST
def send_message(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Requête JSON invalide.'}, status=400)

    content = str(payload.get('message', '')).strip()
    if not content:
        return JsonResponse({'error': 'Le message ne peut pas être vide.'}, status=400)
    if len(content) > settings.CHAT_MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': f'Message limité à {settings.CHAT_MAX_MESSAGE_LENGTH} caractères.'}, status=400)

    conversation = _get_conversation(request)
    user_message = Message.objects.create(conversation=conversation, role=Message.Role.USER, content=content)
    history = list(conversation.messages.order_by('-created_at', '-id')[:settings.CHAT_HISTORY_LIMIT])[::-1]

    history_payload = [{'role': message.role, 'content': message.content} for message in history]

    def event_stream():
        chunks = []
        try:
            for chunk in stream_assistant_reply(history_payload, session_key=conversation.session_key):
                chunks.append(chunk)
                yield f'data: {json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}\n\n'
            reply = ''.join(chunks).strip()
            if reply:
                Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=reply)
            yield f'data: {json.dumps({"type": "done"})}\n\n'
        except (AIProviderError, AIServiceError) as exc:
            error = str(exc) or "L'assistant est momentanément indisponible."
            yield f'data: {json.dumps({"type": "error", "error": error}, ensure_ascii=False)}\n\n'

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

# Create your views here.
