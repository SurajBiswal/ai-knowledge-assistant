import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Create an instance of the Settings class to access the configuration values throughout the application.
settings = Settings()

DATABASE_URL = os.getenv("DATABASE_URL")