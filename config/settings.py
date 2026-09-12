import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Create a .env file with DISCORD_TOKEN=your_token"
    )

DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

# Bot-wide constants — expand as new systems are added
DEFAULT_EMBED_COLOR = 0x5865F2  # Discord blurple