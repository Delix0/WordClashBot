# database.py
import aiosqlite

DB_NAME = "words_bot.db"

async def init_db():
    """Создает таблицу пользователей, если её нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                total_score INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def update_user_stat(user_id: int, username: str, score_add: int = 0, win: bool = False):
    """Обновляет статистику игрока."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, есть ли юзер, если нет - создаем
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)
        """, (user_id, username))
        
        # Обновляем данные
        query = """
            UPDATE users 
            SET total_score = total_score + ?,
                games_played = games_played + 1,
                username = ?
        """
        params = [score_add, username]
        
        if win:
            query = """
                UPDATE users 
                SET total_score = total_score + ?,
                    games_played = games_played + 1,
                    wins = wins + 1,
                    username = ?
            """
        
        query += " WHERE user_id = ?"
        params.append(user_id)
        
        await db.execute(query, tuple(params))
        await db.commit()

async def get_top_players(limit=10):
    """Получает топ игроков по очкам."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username, total_score, wins FROM users ORDER BY total_score DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()