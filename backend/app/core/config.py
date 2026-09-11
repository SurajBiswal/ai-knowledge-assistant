import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY"
    )

    JWT_ALGORITHM = os.getenv(
        "JWT_ALGORITHM"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )
    )

# Create an instance of the Settings class to access the configuration values throughout the application.
settings = Settings()

DATABASE_URL = os.getenv("DATABASE_URL")