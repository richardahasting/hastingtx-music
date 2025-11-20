"""Configuration management for HastingTX Music application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'hastingtx_music')
    DB_USER = os.getenv('DB_USER', 'richard')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    @property
    def DATABASE_URL(self):
        """Construct database URL from components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB default
    ALLOWED_EXTENSIONS = {'mp3'}

    # Security settings
    ADMIN_IP_WHITELIST = os.getenv('ADMIN_IP_WHITELIST', '127.0.0.1,::1').split(',')

    # Application settings
    SITE_NAME = os.getenv('SITE_NAME', 'HastingTX Music')
    SONGS_PER_PAGE = int(os.getenv('SONGS_PER_PAGE', 50))

    @staticmethod
    def init_app(app):
        """Initialize application with this config."""
        # Ensure upload folder exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


config = Config()
