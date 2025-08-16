from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import Base, engine
from routers.auth import auth_router
from routers.user import user_router
from routers.questionnaire import quest_router
from routers.chat import chat_router
from routers.tracking import tracking_router
from models.role import Role
from models.user import User
from models.questionnaire import UserQuestionnaire
import logging

from fastapi.exceptions import RequestValidationError

app = FastAPI()
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(quest_router)
app.include_router(chat_router)
app.include_router(tracking_router)

# ✅ Setup basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

# ✅ Middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.info(f"➡️ Incoming request: {request.method} {request.url.path}")
    logger.info(f"🔸 Body: {body.decode('utf-8') if body else '<empty>'}")
    response = await call_next(request)
    logger.info(f"⬅️ Response status: {response.status_code}")
    return response

logger = logging.getLogger("uvicorn.error")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Validation error on %s %s: %s", request.method, request.url, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
