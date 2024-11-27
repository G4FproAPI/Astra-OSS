from fastapi import APIRouter
from utils.provider_selector import get_all_models
import json

with open('model_multipliers.json', 'r') as f:
    MODEL_CONFIG = json.load(f)

router = APIRouter()

@router.get("/v1/models")
async def get_models():
    models = await get_all_models()
    
    
    unique_models = set(model for sublist in models for model in sublist)
    
    return {
        "data": [
            {
                "id": model,
                "object": "model",
                "created": 0,
                "owned_by": "G4F.PRO",
                "multiplier": MODEL_CONFIG.get(model, {}).get('multiplier', 1),
                "restrictions": MODEL_CONFIG.get(model, {}).get('restrictions', {
                    "free": True,
                    "premium": True,
                    "enterprise": True
                })
            }
            for model in unique_models
        ]
    }
