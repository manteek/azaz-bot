import discord
from datetime import datetime, timezone

from config.settings import DEFAULT_EMBED_COLOR


def base_embed(title: str, description: str = "", color: int = DEFAULT_EMBED_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def success_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(f"✅ {title}", description, color=0x57F287)


def error_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(f"❌ {title}", description, color=0xED4245)