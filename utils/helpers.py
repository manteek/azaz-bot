import discord


def format_duration(seconds: int) -> str:
    """Turn a second count into a human string, e.g. 3665 -> '1h 1m 5s'."""
    parts = []
    for label, unit in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, seconds = divmod(seconds, unit)
        if value:
            parts.append(f"{value}{label}")
    return " ".join(parts) or "0s"


def is_hierarchy_safe(actor: discord.Member, target: discord.Member) -> bool:
    """True if actor's top role outranks target's top role (and target isn't the guild owner)."""
    if target == actor.guild.owner:
        return False
    return actor.top_role > target.top_role