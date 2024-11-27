import aiohttp
import os
from typing import Optional

DISCORD_WEBHOOK_URL = "not today buckaroo"

async def send_discord_webhook(title: str, message: str, color: Optional[int] = None):

    if not DISCORD_WEBHOOK_URL:
        return
    
    if color is None:
        color = 0x00ff00  
    
    embed = {
        "title": title,
        "description": message,
        "color": color
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(
                DISCORD_WEBHOOK_URL,
                json={"embeds": [embed]}
            )
        except Exception as e:
            print(f"Failed to send Discord webhook: {e}") 
