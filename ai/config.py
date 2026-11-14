import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# LLM Configuration
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# API Configuration
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "Scholarship AI Intelligence API"

# Allowed CORS Origins (Vite React frontend, local dev, preview domains)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*",
]

