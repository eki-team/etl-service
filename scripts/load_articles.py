"""
Standalone script to load articles from JSON files into MongoDB
Can be run independently without starting the FastAPI server
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.startup import startup_initialization


if __name__ == "__main__":
    print("🔄 Running standalone article loader...")
    asyncio.run(startup_initialization())
    print("✅ Done!")
