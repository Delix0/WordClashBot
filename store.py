# store.py
# Структура:
# games[chat_id] = {
#     "status": "registration" | "running",
#     "players": [{"id": 123, "score" "name": "User", "alive": True}, ...],
#     "current_player_index": 0,
#     "used_words": set(),
#     "last_letter": None,
#     "timer_task": asyncio.Task,   # Задача таймера хода
#     "start_task": asyncio.Task    # Задача таймера автостарта
# }

games = {}