from .exceptions import AIServiceError
from .exceptions import AIProviderError
from .providers import GeminiProvider
from .schemas import ChatMessage
from .tools import execute_tool_call, gemini_tool_declarations
from pydantic import ValidationError


def generate_assistant_reply(history: list[dict[str, str]], session_key: str | None = None) -> str:
    try:
        messages = [ChatMessage.model_validate(item) for item in history]
        provider = GeminiProvider()
        if session_key is None:
            return provider.generate_reply(messages).content

        declarations = gemini_tool_declarations()
        result = provider.generate_with_tools(messages, declarations)
        for _ in range(3):
            if not result.calls:
                return result.text or 'La demande a été traitée.'
            tool_results = [
                (call.name, execute_tool_call(call, session_key))
                for call in result.calls
            ]
            result = provider.continue_with_tool_results(messages, declarations, result, tool_results)
        return result.text or 'Les opérations demandées ont été effectuées.'
    except (AIServiceError, AIProviderError):
        raise
    except ValidationError as exc:
        raise AIServiceError('Impossible de générer la réponse de l assistant.') from exc


def stream_assistant_reply(history: list[dict[str, str]], session_key: str):
    """Diffuse les morceaux de réponse tout en gardant Django maître des tools."""
    try:
        messages = [ChatMessage.model_validate(item) for item in history]
        provider = GeminiProvider()
        declarations = gemini_tool_declarations()
        result = yield from provider.stream_with_tools(messages, declarations)
        for _ in range(3):
            if not result.calls:
                return
            tool_results = [
                (call.name, execute_tool_call(call, session_key))
                for call in result.calls
            ]
            # Le résultat est déjà validé et produit par Django. Le renvoyer
            # directement évite un second appel Gemini, réduit la latence et
            # évite de consommer deux fois le quota pour chaque action.
            report = '\n'.join(result_text for _, result_text in tool_results)
            yield report
            return
    except (AIServiceError, AIProviderError):
        raise
    except ValidationError as exc:
        raise AIServiceError('Impossible de générer la réponse de l assistant.') from exc
