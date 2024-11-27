import importlib
import os
import random
from typing import List, Type
from utils.baseprovider import BaseProvider, BaseTTSProvider
from pystyle import Colorate, Colors

def load_providers() -> List[Type[BaseProvider]]:
    providers = []
    providers_dir = 'providers'
    for filename in os.listdir(providers_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            module = importlib.import_module(f'{providers_dir}.{module_name}')
            for attr in dir(module):
                cls = getattr(module, attr)
                if isinstance(cls, type) and (
                    issubclass(cls, BaseProvider) or issubclass(cls, BaseTTSProvider)
                ) and cls not in (BaseProvider, BaseTTSProvider):
                    providers.append(cls())
    return providers

def load_tts_providers() -> List[Type[BaseTTSProvider]]:
    providers = []
    directories = ['providers', os.path.join('providers', 'tts')]
    
    for providers_dir in directories:
        if not os.path.exists(providers_dir):
            continue 
        for filename in os.listdir(providers_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                module_path = f'{providers_dir.replace(os.sep, ".")}.{module_name}'
                module = importlib.import_module(module_path)
                for attr in dir(module):
                    cls = getattr(module, attr)
                    if isinstance(cls, type) and issubclass(cls, BaseTTSProvider) and cls is not BaseTTSProvider:
                        providers.append(cls())
    return providers

def select_provider(chat_request, type: str = "chat"):
    providers = load_providers()
    
    
    suitable_providers = [
        provider for provider in providers
        if (type == "tts" and chat_request["model"] in provider.models and chat_request["voice"] in provider.voices) or
           (type != "tts" and (not chat_request.get("stream") or provider.supports_streaming) and chat_request["model"] in provider.models)
    ]
    
    if not suitable_providers:
        raise ValueError("No suitable provider found for the given request")

    priority_providers = [provider for provider in suitable_providers if provider.priority]
    chosen_provider = random.choice(priority_providers) if priority_providers else random.choice(suitable_providers)
    
    provider_type = "priority provider" if priority_providers else "provider"
    print(Colorate.Vertical(Colors.blue_to_purple, f"Using {provider_type}: {chosen_provider.__class__.__name__}"))
    
    return chosen_provider

def get_tts_provider(args: dict):
    return select_provider(args, type="tts")

def get_all_tts_models():
    providers = load_tts_providers()
    return [provider.models for provider in providers], [provider.voices for provider in providers]

async def handle_request(args: dict):
    provider = select_provider(args)
    async for response in provider.create_chat_completion(args):
        yield response

async def get_all_models():
    providers = load_providers()
    return [provider.models for provider in providers]
