from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from utils.schemas import ChatCompletionsRequestSchema
from utils.provider_selector import select_provider
from utils.mongo import get_user_by_api_key, add_usage
from utils.discord_webhook import send_discord_webhook
import json
import os
import logging
import time

with open('model_multipliers.json', 'r') as f:
    MODEL_CONFIG = json.load(f)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    start_time = time.time()
    try:
        logger.info("Starting chat completion request")
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        api_key = auth_header.replace('Bearer ', '')
        
        user = await get_user_by_api_key(api_key)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
                
        if user["banned"]:
            raise HTTPException(status_code=403, detail="User is banned")
            
        if user["usage"] >= user["max_usage_per_day"]:
            raise HTTPException(status_code=429, detail="Not enough credits")

        body = await request.json()
        logger.info("Request body received")
        chat_request = body
        
        if 'stream' not in chat_request:
            chat_request['stream'] = False
        
        model = chat_request.get('model', 'gpt-3.5-turbo')
        if model in MODEL_CONFIG:
            if not MODEL_CONFIG[model]['restrictions'].get(user['plan'], False):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Your plan ({user['plan']}) doesn't have access to {model}"
                )
            
            usage_multiplier = MODEL_CONFIG[model].get('multiplier', 1)
        else:
            usage_multiplier = 1

        if chat_request["stream"]:
            logger.info("Starting streaming response")
            async def event_generator():
                async for chunk in select_provider(chat_request).create_chat_completion(chat_request):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            await add_usage(user["user_id"], float(usage_multiplier))
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            provider = select_provider(chat_request)
            provider_name = str(provider.__class__.__name__)[:3]
            response = None
            async for resp in provider.create_chat_completion(chat_request):
                response = resp
                await add_usage(user["user_id"], float(usage_multiplier))
                
            request_time = round(time.time() - start_time, 2)
            await send_discord_webhook(
                "REQUEST LOG!",
                f"User: <@{user['user_id']}>\n"
                f"Model: {chat_request.get('model', 'gpt-3.5-turbo')}\n"
                f"Provider: {provider_name}\n"
                f"Request Time: {request_time}s"
            )
            return response

    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {http_exc.detail}")
        await send_discord_webhook(
            "ERROR LOG!",
            f"Status: {http_exc.status_code}\n"
            f"Error: {http_exc.detail}"
        )
        if http_exc.status_code in [401, 403, 429]:
            raise http_exc
        raise HTTPException(status_code=469, detail=str(http_exc.detail))
    except Exception as e:
        logger.error(f"Unexpected error in chat_completions: {str(e)}")
        await send_discord_webhook(
            "CRITICAL ERROR!",
            f"Error: {str(e)}"
        )
        raise HTTPException(status_code=469, detail="Internal server error")
    
