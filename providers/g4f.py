from utils.baseprovider import BaseProvider
import g4f
from utils.common import generate_chunk, generate_response

class G4FProvider(BaseProvider):
    def __init__(self):
        self.models = [
            "llama-3.1-8b-instruct",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest",
        ]
        self.aliases = {
            "llama-3.1-8b-instruct": "llama-3.1-8b",
            "gemini-1.5-flash-latest": "gemini-flash",
            "gemini-1.5-pro-latest": "gemini-pro",
        }
        self.supports_streaming = True
        self.priority = True

    async def create_chat_completion(self, args): 
        model = args.get("model", "llama-3.1-8b-instruct")
        messages = args.get("messages", [])
        stream = args.get("stream", False)
        if stream:
            response = g4f.ChatCompletion.create(model=self.aliases.get(model, model), messages=messages, stream=True)
            for chunk in response:
                yield generate_chunk(chunk, model)
        else:
            response = g4f.ChatCompletion.create(model=self.aliases.get(model, model), messages=messages)
            yield generate_response(response, model)
