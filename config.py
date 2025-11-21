from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 180

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_MAX_FILE_SIZE: int = 10485760  # 10MB in bytes
    LOG_BACKUP_COUNT: int = 5
    LOG_COLORS: str = "true"
    LOG_RESPONSE_BODY: str = "false"
    
    # Environment
    ENVIRONMENT: str = "development"

    UPLOAD_URL: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_SES_REGION: str
    SES_FROM_EMAIL: str

    class Config:
        env_file = ".env"

settings = Settings()
