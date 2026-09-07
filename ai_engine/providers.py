from dataclasses import dataclass

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
import httpx

from django.conf import settings

from .exceptions import AIProviderError
from .prompts import DEFAULT_SYSTEM_PROMPT
from .schemas import AssistantResponse, ChatMessage, ToolCall


@dataclass
class ProviderToolResult:
    text: str
    calls: list[ToolCall]
    model_content: genai_types.Content | None = None


class GeminiProvider:
    def __init__(self, model=None, temperature=None):
        self.model = model or settings.GEMINI_MODEL
        self.temperature = settings.GEMINI_TEMPERATURE if temperature is None else temperature
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise AIProviderError('La configuration du fournisseur IA est incomplète.')
        self.client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(
                timeout=settings.GEMINI_TIMEOUT_MS,
                retry_options=genai_types.HttpRetryOptions(attempts=settings.GEMINI_RETRY_ATTEMPTS),
            ),
        )

    def generate_reply(self, history: list[ChatMessage]) -> AssistantResponse:
        conversation = '\n'.join(f'{message.role.upper()}: {message.content}' for message in history)
        try:
            response = self._generate_content(self.model, conversation)
        except genai_errors.ClientError as exc:
            # Google a retiré 2.5-flash pour certaines nouvelles clés. Le modèle
            # reste le défaut configuré, mais on assure la compatibilité immédiate.
            if exc.code != 404 or self.model != 'gemini-2.5-flash':
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc
            try:
                response = self._generate_content('gemini-3.6-flash', conversation)
            except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as fallback_exc:
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from fallback_exc
        except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as exc:
            raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc

        try:
            text = (response.text or '').strip()
            if not text:
                raise AIProviderError('Le fournisseur IA a renvoyé une réponse vide.')
            return AssistantResponse(content=text)
        except AIProviderError:
            raise

    def _generate_content(self, model: str, conversation, tool_declarations=None):
        return self.client.models.generate_content(
            model=model,
            contents=conversation,
            config=genai.types.GenerateContentConfig(
                system_instruction=DEFAULT_SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                tools=[genai_types.Tool(functionDeclarations=tool_declarations)] if tool_declarations else None,
            ),
        )

    def generate_with_tools(self, history: list[ChatMessage], declarations) -> ProviderToolResult:
        contents = self._history_contents(history)
        try:
            response = self._generate_content(self.model, contents, declarations)
        except genai_errors.ClientError as exc:
            if exc.code == 429:
                raise AIProviderError('Le quota Gemini est temporairement atteint. Réessayez plus tard ou vérifiez votre forfait.') from exc
            if exc.code != 404 or self.model != 'gemini-2.5-flash':
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc
            try:
                self.model = 'gemini-3.6-flash'
                response = self._generate_content('gemini-3.6-flash', contents, declarations)
            except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as fallback_exc:
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from fallback_exc
        except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as exc:
            raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc
        return self._parse_tool_response(response)

    def continue_with_tool_results(self, history, declarations, previous: ProviderToolResult, results: list[tuple[str, str]]) -> ProviderToolResult:
        contents = self._history_contents(history)
        if previous.model_content is not None:
            contents.append(previous.model_content)
        for name, result in results:
            contents.append(genai_types.Content(
                role='user',
                parts=[genai_types.Part.from_function_response(name=name, response={'result': result})],
            ))
        try:
            response = self._generate_content(self.model, contents, declarations)
        except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as exc:
            raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc
        return self._parse_tool_response(response)

    def stream_with_tools(self, history: list[ChatMessage], declarations):
        contents = self._history_contents(history)
        try:
            return (yield from self._stream_model(self.model, contents, declarations))
        except genai_errors.ClientError as exc:
            if exc.code == 429:
                raise AIProviderError('Le quota Gemini est temporairement atteint. Réessayez plus tard ou vérifiez votre forfait.') from exc
            if exc.code != 404 or self.model != 'gemini-2.5-flash':
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc
            self.model = 'gemini-3.6-flash'
            try:
                return (yield from self._stream_model(self.model, contents, declarations))
            except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as fallback_exc:
                raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from fallback_exc
        except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as exc:
            raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc

    def stream_with_tool_results(self, history, declarations, previous: ProviderToolResult, results: list[tuple[str, str]]):
        contents = self._history_contents(history)
        if previous.model_content is not None:
            contents.append(previous.model_content)
        for name, result in results:
            contents.append(genai_types.Content(
                role='user',
                parts=[genai_types.Part.from_function_response(name=name, response={'result': result})],
            ))
        try:
            return (yield from self._stream_model(self.model, contents, declarations))
        except (genai_errors.APIError, genai_errors.UnknownApiResponseError, httpx.HTTPError, ValueError) as exc:
            raise AIProviderError('Le fournisseur IA est momentanément indisponible.') from exc

    def _stream_model(self, model: str, contents, tool_declarations=None):
        response_stream = self.client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=DEFAULT_SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                tools=[genai_types.Tool(functionDeclarations=tool_declarations)] if tool_declarations else None,
            ),
        )
        parts = []
        text_parts = []
        calls = []
        for chunk in response_stream:
            candidate = chunk.candidates[0] if chunk.candidates else None
            if not candidate or not candidate.content:
                continue
            for part in candidate.content.parts or []:
                parts.append(part)
                if part.text:
                    text_parts.append(part.text)
                    yield part.text
                if part.function_call:
                    calls.append(ToolCall(name=part.function_call.name, arguments=dict(part.function_call.args or {})))
        return ProviderToolResult(
            text=''.join(text_parts).strip(),
            calls=calls,
            model_content=genai_types.Content(role='model', parts=parts) if parts else None,
        )

    @staticmethod
    def _history_contents(history):
        return [genai_types.Content(
            role='model' if message.role == 'assistant' else 'user',
            parts=[genai_types.Part.from_text(text=message.content)],
        ) for message in history]

    @staticmethod
    def _parse_tool_response(response) -> ProviderToolResult:
        candidate = response.candidates[0] if response.candidates else None
        model_content = candidate.content if candidate else None
        calls = []
        text_parts = []
        if candidate and candidate.content:
            for part in candidate.content.parts or []:
                if part.text:
                    text_parts.append(part.text)
                if part.function_call:
                    calls.append(ToolCall(name=part.function_call.name, arguments=dict(part.function_call.args or {})))
        return ProviderToolResult(text='\n'.join(text_parts).strip(), calls=calls, model_content=model_content)
