from dataclasses import dataclass, field
import abc
from typing import AsyncGenerator

@dataclass
class ChatCompletionArgs:
    messages: list[dict]
    model: str
    stream: bool = False
    kwargs: dict = field(default_factory=dict)

class BaseProvider(abc.ABC):
    @abc.abstractmethod
    def create_chat_completion(self, args: ChatCompletionArgs) -> dict:
        pass

class BaseTTSProvider(abc.ABC):
    @abc.abstractmethod
    def generate_audio(self, text: str, voice: str = "nova") -> str:
        pass

class BaseUpscaleProvider(abc.ABC):
    @abc.abstractmethod
    def create_upscaling_task(self, args) -> AsyncGenerator[dict, None]:
        pass
