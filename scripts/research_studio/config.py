import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Global Paths
BASE_PATH = Path("research")
SOURCES_FILE = BASE_PATH / "sources.md"

# Ensure directories exist
(BASE_PATH / "youtube-transcripts").mkdir(parents=True, exist_ok=True)
(BASE_PATH / "linkedin-posts").mkdir(parents=True, exist_ok=True)
