import random
import time
import string
from typing import List, Dict, Any
def generate_id() -> str:
    return f"chatcmpl-{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

def generate_chunk(response: str, model: str) -> dict:
    return {
        "id": generate_id(),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"delta": {"content": response}}]
    }

def get_random_proxy() -> str:
    with open("utils/proxies.txt", "r") as f:
        proxies = f.read().splitlines()
    proxy = random.choice(proxies)
    host, port, username, password = proxy.split(":")
    return f"http://{username}:{password}@{host}:{port}"

def generate_response(response: str, model: str) -> dict:
    return {
        "id": generate_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": response}}]
    }


def stringify_message(messages: List[Dict[str, Any]]) -> str:
    return '\n'.join(
        f"{m['role'].capitalize()}: {m['content']}\n"
        for m in messages if isinstance(m['content'], str)
    )+"\nAssistant:"
