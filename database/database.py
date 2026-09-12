import aiosqlite
from datetime import datetime, timezone

from config.settings import DATABASE_PATH


def _xp_for_level(level: int) -> int:
    """Total XP required to reach this level. Standard curve: gets steeper each level."""
    return 5 * (level ** 2) + 50 * level + 100


class Database:
    def __init__(self, path: str = DATABASE_PATH):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                goodbye_channel_id INTEGER,
                log_channel_id INTEGER,
                autorole_id INTEGER,
                xp_enabled INTEGER DEFAULT 1,
                xp_min INTEGER DEFAULT 15,
                xp_max INTEGER DEFAULT 25,
                xp_cooldown INTEGER DEFAULT 60,
                level_up_channel_id INTEGER,
                economy_currency_name TEXT DEFAULT 'coins',
                daily_amount INTEGER DEFAULT 100,
                antispam_enabled INTEGER DEFAULT 1,
                antispam_msg_limit INTEGER DEFAULT 5,
                antispam_interval INTEGER DEFAULT 5,
                antispam_timeout_seconds INTEGER DEFAULT 60
            );

            CREATE TABLE IF NOT EXISTS xp (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                last_xp_at TEXT,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS level_roles (
                guild_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, level)
            );

            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER DEFAULT 0,
                last_daily TEXT,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS self_roles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER,
                remind_at TEXT NOT NULL,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                fired INTEGER DEFAULT 0
            );
        """)
        await self.conn.commit()
        await self._migrate_add_column("guild_config", "welcome_banner_url", "TEXT")

    async def _migrate_add_column(self, table: str, column: str, col_type: str):
        cursor = await self.conn.execute(f"PRAGMA table_info({table})")
        columns = [row["name"] for row in await cursor.fetchall()]
        if column not in columns:
            await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            await self.conn.commit()

    # --- Warnings ---

    async def add_warning(self, guild_id, user_id, moderator_id, reason):
        await self.conn.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason),
        )
        await self.conn.commit()

    async def get_warnings(self, guild_id, user_id):
        cursor = await self.conn.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (guild_id, user_id),
        )
        return await cursor.fetchall()

    # --- Guild config ---

    async def get_guild_config(self, guild_id: int) -> aiosqlite.Row:
        cursor = await self.conn.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await self.conn.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await self.conn.commit()
            cursor = await self.conn.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return row

    async def update_guild_config(self, guild_id: int, **fields):
        await self.get_guild_config(guild_id)  # ensure row exists
        columns = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [guild_id]
        await self.conn.execute(f"UPDATE guild_config SET {columns} WHERE guild_id = ?", values)
        await self.conn.commit()

    # --- XP / leveling ---

    async def get_xp(self, guild_id: int, user_id: int) -> aiosqlite.Row:
        cursor = await self.conn.execute(
            "SELECT * FROM xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        row = await cursor.fetchone()
        if row is None:
            await self.conn.execute(
                "INSERT INTO xp (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)", (guild_id, user_id)
            )
            await self.conn.commit()
            cursor = await self.conn.execute(
                "SELECT * FROM xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
            )
            row = await cursor.fetchone()
        return row

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int, bool]:
        """Adds XP, returns (new_xp, new_level, leveled_up)."""
        row = await self.get_xp(guild_id, user_id)
        new_xp = row["xp"] + amount
        new_level = row["level"]
        leveled_up = False
        while new_xp >= _xp_for_level(new_level + 1):
            new_level += 1
            leveled_up = True

        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE xp SET xp = ?, level = ?, last_xp_at = ? WHERE guild_id = ? AND user_id = ?",
            (new_xp, new_level, now, guild_id, user_id),
        )
        await self.conn.commit()
        return new_xp, new_level, leveled_up

    async def get_xp_leaderboard(self, guild_id: int, limit: int = 10):
        cursor = await self.conn.execute(
            "SELECT * FROM xp WHERE guild_id = ? ORDER BY xp DESC LIMIT ?", (guild_id, limit)
        )
        return await cursor.fetchall()

    async def set_level_role(self, guild_id: int, level: int, role_id: int):
        await self.conn.execute(
            "INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id",
            (guild_id, level, role_id),
        )
        await self.conn.commit()

    async def get_level_roles(self, guild_id: int):
        cursor = await self.conn.execute("SELECT * FROM level_roles WHERE guild_id = ?", (guild_id,))
        return await cursor.fetchall()

    # --- Economy ---

    async def get_balance(self, guild_id: int, user_id: int) -> int:
        cursor = await self.conn.execute(
            "SELECT balance FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        row = await cursor.fetchone()
        if row is None:
            await self.conn.execute(
                "INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 0)", (guild_id, user_id)
            )
            await self.conn.commit()
            return 0
        return row["balance"]

    async def update_balance(self, guild_id: int, user_id: int, delta: int) -> int:
        current = await self.get_balance(guild_id, user_id)
        new_balance = max(0, current + delta)
        await self.conn.execute(
            "UPDATE economy SET balance = ? WHERE guild_id = ? AND user_id = ?",
            (new_balance, guild_id, user_id),
        )
        await self.conn.commit()
        return new_balance

    async def get_last_daily(self, guild_id: int, user_id: int) -> str | None:
        cursor = await self.conn.execute(
            "SELECT last_daily FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return row["last_daily"] if row else None

    async def set_last_daily(self, guild_id: int, user_id: int):
        await self.get_balance(guild_id, user_id)  # ensure row exists
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE economy SET last_daily = ? WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )
        await self.conn.commit()

    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10):
        cursor = await self.conn.execute(
            "SELECT * FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?", (guild_id, limit)
        )
        return await cursor.fetchall()

    # --- Self-assignable roles ---

    async def add_self_role(self, guild_id: int, role_id: int, label: str):
        await self.conn.execute(
            "INSERT INTO self_roles (guild_id, role_id, label) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, role_id) DO UPDATE SET label = excluded.label",
            (guild_id, role_id, label),
        )
        await self.conn.commit()

    async def remove_self_role(self, guild_id: int, role_id: int):
        await self.conn.execute(
            "DELETE FROM self_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id)
        )
        await self.conn.commit()

    async def get_self_roles(self, guild_id: int):
        cursor = await self.conn.execute("SELECT * FROM self_roles WHERE guild_id = ?", (guild_id,))
        return await cursor.fetchall()

    async def get_guilds_with_self_roles(self):
        cursor = await self.conn.execute("SELECT DISTINCT guild_id FROM self_roles")
        return await cursor.fetchall()

    # --- Reminders ---

    async def add_reminder(self, user_id: int, channel_id: int, guild_id: int | None, remind_at: str, message: str):
        await self.conn.execute(
            "INSERT INTO reminders (user_id, channel_id, guild_id, remind_at, message) VALUES (?, ?, ?, ?, ?)",
            (user_id, channel_id, guild_id, remind_at, message),
        )
        await self.conn.commit()

    async def get_due_reminders(self, now_iso: str):
        cursor = await self.conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 AND remind_at <= ?", (now_iso,)
        )
        return await cursor.fetchall()

    async def mark_reminder_fired(self, reminder_id: int):
        await self.conn.execute("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))
        await self.conn.commit()