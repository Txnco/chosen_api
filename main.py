from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from database import Base, engine

from routers.auth import auth_router
from routers.user import user_router
from routers.questionnaire import quest_router
from routers.chat import chat_router
from routers.tracking import tracking_router
from routers.event import event_router
from routers.water import water_router
from routers.motivational_quote import quote_router
from routers.notification import notification_router

from models.water import WaterGoal, WaterTracking
from models.role import Role
from models.user import User
from models.event import Event, EventCopy
from models.questionnaire import UserQuestionnaire

from functions.fcm import FCMService

from starlette.responses import StreamingResponse, FileResponse
import logging
import logging.handlers
import time
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError



app = FastAPI(title="chosen-api", version="1.0.0")
Base.metadata.create_all(bind=engine)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
    "https://admin.chosen-international.com", 
    "https://admin.chosen-international.com/api"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files directory for uploads
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ✅ Create logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# ✅ Setup logging configuration inline
def setup_logging():
    """Setup comprehensive logging"""
    
    # Custom formatter with colors
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
        
        def format(self, record):
            if hasattr(record, 'color') and record.color:
                level_color = self.COLORS.get(record.levelname, '')
                reset_color = self.COLORS['RESET']
                original_levelname = record.levelname
                record.levelname = f"{level_color}{record.levelname}{reset_color}"
                formatted = super().format(record)
                record.levelname = original_levelname
                return formatted
            return super().format(record)
    
    # Create main logger
    logger = logging.getLogger("chosen_api")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Main log file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "api.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Error log file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.propagate = False
    
    return logger

# ✅ Initialize logger
logger = setup_logging()

# ✅ Helper functions
def mask_sensitive_data(data):
    """Mask sensitive fields in log data"""
    if not isinstance(data, dict):
        return data
    
    sensitive_fields = {'password', 'token', 'secret', 'authorization', 'access_token'}
    masked_data = data.copy()
    
    for key, value in masked_data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            masked_data[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
    
    return masked_data

def format_json_for_log(data, max_length=1000):
    """Format data as JSON for logging"""
    try:
        if isinstance(data, dict):
            data = mask_sensitive_data(data)
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if len(json_str) > max_length:
            return json_str[:max_length] + "... [truncated]"
        
        return json_str
    except Exception:
        return str(data)


def _safe_content_length(resp) -> str:
    try:
        # Prefer explicit header if present
        cl = resp.headers.get("content-length")
        if cl is not None:
            return cl  # header values are strings
        # If it's a streaming/file response, length is typically unknown
        if isinstance(resp, (StreamingResponse, FileResponse)):
            return "streaming"
    except Exception:
        pass
    return "unknown"

SAFE_BODY_LOG_BYTES = 64_000  # 64KB cap to avoid huge logs
TEXT_TYPES_PREFIXES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "text/",
)

def _is_textual(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    ct = content_type.split(";")[0].strip().lower()
    return ct.startswith(TEXT_TYPES_PREFIXES)

def _is_multipart(content_type: Optional[str]) -> bool:
    return bool(content_type and content_type.lower().startswith("multipart/form-data"))

# ✅ Enhanced middleware - FIXED for file uploads
@app.middleware("http")
async def comprehensive_logging_middleware(request: Request, call_next):
    # Generate request id & timing
    request_id = f"req_{int(time.time() * 1000)}"
    start_time = time.time()

    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"🔵 [{request_id}] {request.method} {request.url.path} | Client: {client_ip}", extra={"color": True})

    if request.query_params:
        logger.info(f"🔍 [{request_id}] Query: {dict(request.query_params)}", extra={"color": True})

    # ----- Request body logging (safe) -----
    content_type = request.headers.get("content-type", "")
    content_length_hdr = request.headers.get("content-length")
    try:
        content_length = int(content_length_hdr) if content_length_hdr else None
    except ValueError:
        content_length = None

    # CRITICAL FIX: Don't read request body for multipart requests
    if _is_multipart(content_type):
        # Don't try to read file bytes - this breaks file uploads
        logger.info(f"📄 [{request_id}] Body: <multipart/form-data with files: {content_length or 'unknown'} bytes>", extra={"color": True})
    elif _is_textual(content_type):
        try:
            # Only read if not too large
            if content_length and content_length > SAFE_BODY_LOG_BYTES:
                logger.info(
                    f"📄 [{request_id}] Body: <{content_type} {content_length} bytes: skipped (too large)>",
                    extra={"color": True},
                )
            else:
                # SAFE: Only read body for non-multipart requests
                raw = await request.body()  # Starlette caches this, downstream can still read
                if len(raw) > SAFE_BODY_LOG_BYTES:
                    raw = raw[:SAFE_BODY_LOG_BYTES]
                    truncated = True
                else:
                    truncated = False

                # Try JSON pretty print first
                if content_type.lower().startswith("application/json"):
                    try:
                        parsed = json.loads(raw.decode("utf-8"))
                        parsed = mask_sensitive_data(parsed)  # Mask sensitive data
                        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                        if truncated:
                            formatted += "\n... [truncated]"
                        logger.info(f"📄 [{request_id}] Body (JSON):\n{formatted}", extra={"color": True})
                    except Exception:
                        # Fallback to plain text
                        text = raw.decode("utf-8", errors="replace")
                        if truncated:
                            text += "... [truncated]"
                        logger.info(f"📄 [{request_id}] Body (text): {text}", extra={"color": True})
                else:
                    # urlencoded / text/*
                    text = raw.decode("utf-8", errors="replace")
                    if truncated:
                        text += "... [truncated]"
                    logger.info(f"📄 [{request_id}] Body (text): {text}", extra={"color": True})
        except Exception as e:
            # Never fail the request because of logging
            logger.error(f"❌ [{request_id}] Error reading request body: {e}", extra={"color": True})
    else:
        # Unknown/binary type
        if content_length is not None:
            logger.info(
                f"📄 [{request_id}] Body: <{content_type or 'unknown type'} {content_length} bytes: not logged>",
                extra={"color": True},
            )
        else:
            logger.info(
                f"📄 [{request_id}] Body: <{content_type or 'unknown type'}: not logged>",
                extra={"color": True},
            )

    # Masked auth header
    if request.headers.get("authorization"):
        logger.info(f"🔑 [{request_id}] Auth: Bearer ***", extra={"color": True})

    # ----- Call downstream -----
    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Status emoji
        emoji = "✅" if response.status_code < 300 else "🔄" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"

        content_length_resp = response.headers.get("content-length", "unknown")
        content_length_resp = _safe_content_length(response)
        try:
            logger.info(
                f"{emoji} [{request_id}] {response.status_code} | "
                f"{process_time:.3f}s | {content_length_resp} bytes",
                extra={"color": True},
            )
        except Exception as log_err:
            # Never let logging crash the request
            logger.error(f"Response logging failed: {log_err}", extra={"color": True})

        if process_time > 1.0:
            logger.warning(f"🐌 [{request_id}] SLOW REQUEST: {process_time:.3f}s for {request.method} {request.url.path}", extra={"color": True})

        # Log error response bodies for debugging
        if response.status_code >= 400:
            try:
                # Only log error responses that are small and text-based
                body_bytes = getattr(response, "body", None)
                if body_bytes is not None and len(body_bytes) < 1000:
                    try:
                        text = body_bytes.decode("utf-8", errors="replace")
                        logger.info(f"📄 [{request_id}] Error Response: {text}", extra={"color": True})
                    except Exception:
                        logger.info(f"📄 [{request_id}] Error Response: <{len(body_bytes)} bytes, not text>", extra={"color": True})
            except Exception:
                pass

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"💥 [{request_id}] EXCEPTION: {request.method} {request.url.path} | Error: {str(e)} | Time: {process_time:.3f}s",
            exc_info=True,
            extra={"color": True},
        )
        raise

# ✅ Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    
    logger.error(
        f"🔴 VALIDATION ERROR: {request.method} {request.url.path}",
        extra={'color': True}
    )
    logger.error(f"🔴 Details: {format_json_for_log(error_details)}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": error_details,
            "message": "Request validation failed"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"💥 UNHANDLED EXCEPTION: {request.method} {request.url.path} - {str(exc)}",
        exc_info=True,
        extra={'color': True}
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

# ✅ Application lifecycle events
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 CHOSEN API Starting up...", extra={'color': True})
    
    # Initialize Firebase Cloud Messaging
    FCMService.initialize()
    
    logger.info(f"📁 Logs directory: {logs_dir.absolute()}", extra={'color': True})
    logger.info("✅ CHOSEN API Started successfully!", extra={'color': True})

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 CHOSEN API Shutting down...", extra={'color': True})
    logger.info("✅ CHOSEN API Stopped successfully!", extra={'color': True})

# ✅ Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(quest_router)
app.include_router(chat_router)
app.include_router(tracking_router)
app.include_router(water_router)
app.include_router(event_router)
app.include_router(quote_router)
app.include_router(notification_router)

# ✅ Health check endpoint
@app.get("/health")
async def health_check():
    logger.info("💓 Health check requested", extra={'color': True})
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "CHOSEN API is running",
        "version": "1.0.0"
    }

# ✅ Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to CHOSEN API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }