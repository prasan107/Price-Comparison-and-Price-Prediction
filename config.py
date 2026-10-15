from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:password@localhost:5432/price_comparison"

    redis_url: str = "redis://localhost:6379/0"

    # SendGrid - optional
    sendgrid_api_key: str = ""

    # Email
    alert_from_email: str = ""

    # Gmail SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""

    app_env: str = "development"
    secret_key: str = "change-this"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()