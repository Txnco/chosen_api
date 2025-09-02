from fastapi import FastAPI, Request, Response
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
import logging.handlers
import time
import json
import os
from datetime import datetime
from pathlib import Path

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

async def get_request_body(request: Request):
    """Safely get request body"""
    try:
        body = await request.body()
        request._body = body
        return body.decode('utf-8') if body else None
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
        return None

# ✅ Enhanced middleware
@app.middleware("http")
async def comprehensive_logging_middleware(request: Request, call_next):
    # Generate unique request ID and start timing
    request_id = f"req_{int(time.time() * 1000)}"
    start_time = time.time()
    
    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    # Log incoming request
    logger.info(
        f"🔵 [{request_id}] {request.method} {request.url.path} | Client: {client_ip}",
        extra={'color': True}
    )
    
    # Log query parameters
    if request.query_params:
        logger.info(f"🔍 [{request_id}] Query: {dict(request.query_params)}", extra={'color': True})
    
    # Log request body
    body = await get_request_body(request)
    if body:
        try:
            json_body = json.loads(body)
            formatted_body = format_json_for_log(json_body)
            logger.info(f"📄 [{request_id}] Body:\n{formatted_body}", extra={'color': True})
        except json.JSONDecodeError:
            logger.info(f"📄 [{request_id}] Body: {body[:500]}{'...' if len(body) > 500 else ''}", extra={'color': True})
    
    # Log authorization (masked)
    if request.headers.get("authorization"):
        logger.info(f"🔑 [{request_id}] Auth: Bearer ***", extra={'color': True})
    
    try:
        # Process request
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Choose emoji based on status
        if response.status_code < 300:
            emoji = "✅"
        elif response.status_code < 400:
            emoji = "🔄"
        elif response.status_code < 500:
            emoji = "⚠️"
        else:
            emoji = "❌"
        
        # Log response
        content_length = response.headers.get('content-length', 'unknown')
        logger.info(
            f"{emoji} [{request_id}] {response.status_code} | {process_time:.3f}s | {content_length} bytes",
            extra={'color': True}
        )
        
        # Log slow requests
        if process_time > 1.0:
            logger.warning(
                f"🐌 [{request_id}] SLOW REQUEST: {process_time:.3f}s for {request.method} {request.url.path}",
                extra={'color': True}
            )
        
        # Log response body for errors
        if response.status_code >= 400:
            try:
                if hasattr(response, 'body') and response.body:
                    body_content = response.body.decode('utf-8')
                    if len(body_content) > 500:
                        body_content = body_content[:500] + "... [truncated]"
                    logger.info(f"📄 [{request_id}] Response: {body_content}", extra={'color': True})
            except Exception:
                pass
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        logger.error(
            f"💥 [{request_id}] EXCEPTION: {request.method} {request.url.path} | "
            f"Error: {str(e)} | Time: {process_time:.3f}s",
            exc_info=True,
            extra={'color': True}
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