from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class AssistantResponse(BaseModel):
    content: str = Field(min_length=1)


class CreateTaskArguments(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    priority: Literal['high', 'medium', 'low'] = 'medium'


class ListTasksArguments(BaseModel):
    only_pending: bool = False


class UpdateTaskArguments(BaseModel):
    task_id: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal['high', 'medium', 'low'] | None = None
    is_done: bool | None = None

    @model_validator(mode='after')
    def has_changes(self):
        if all(value is None for name, value in self.model_dump().items() if name != 'task_id'):
            raise ValueError('Au moins un champ modifiable est requis.')
        return self


class DeleteTaskArguments(BaseModel):
    task_id: int = Field(gt=0)


class AnalyzeTasksArguments(BaseModel):
    pass


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
