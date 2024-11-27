from fastapi import FastAPI, Request, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from routes.models import router as models_router   
from routes.chatcompletions import router as chatcompletions_router
from fastapi.middleware.cors import CORSMiddleware
from utils.mongo import get_user_by_api_key
import time
from collections import defaultdict

RATE_LIMITS = {
    "free": 8,
    "premium": 30,
    "enterprise": 60
}

request_history = defaultdict(list)

app = FastAPI(docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

app.include_router(models_router)
app.include_router(chatcompletions_router)
@app.exception_handler(HTTPException)
async def custom_404_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": True, "message": "This route does not exist. If you need support, please stop needing support."}
        )
    
    if exc.status_code == 429:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.detail}
    )
    if exc.status_code == 401:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.detail}
        )

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    
    if request.url.path in ["/v1/models", "/v1/models/", "v1/models", "v1/models/"] and request.method == "GET":
        return await call_next(request)

    if request.headers.get("Authorization"):
        api_key = request.headers.get("Authorization").split(" ")[1]
    else:
        return await call_next(request)

    user = await get_user_by_api_key(api_key)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": True, "message": "Invalid API key"}
        )

    rate_limit = RATE_LIMITS.get(user["plan"], RATE_LIMITS["free"])
    
    current_time = time.time()
    request_history[api_key] = [
        timestamp for timestamp in request_history[api_key]
        if current_time - timestamp < 60
    ]
    
    if len(request_history[api_key]) >= rate_limit:
        return JSONResponse(
            status_code=429,
            content={
                "error": True,
                "message": f"Rate limit exceeded. Maximum {rate_limit} requests per minute allowed for {user['plan']} plan."
            }
        )
    
    request_history[api_key].append(current_time)
    
    return await call_next(request)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("templates/index.html", "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@app.get("/docs", response_class=HTMLResponse)
async def read_docs():
    with open("templates/docs.html", "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
