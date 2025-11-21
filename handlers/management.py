# handlers/management.py
import asyncio
import random
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
# Импортируем инструмент для удаления кнопок
from aiogram.types import ReplyKeyboardRemove 

from store import games
from utils.game_logic import start_round
import config
import database

router = Router()

# --- КОМАНДА ДЛЯ УДАЛЕНИЯ КНОПОК ---
@router.message(Command("reset"))
async def cmd_reset(message: types.Message):
    # Просто убирает клавиатуру, если она есть у пользователя
    await message.answer("🗑 Клавиатура убрана.", reply_markup=ReplyKeyboardRemove())
# -----------------------------------

@router.message(Command("startgame"))
async def cmd_startgame(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id in games:
        await message.answer("Игра уже идет или набираются игроки!")
        return

    games[chat_id] = {
        "status": "registration",
        "players": [],
        "current_player_index": 0,
        "used_words": set(),
        "last_letter": None,
        "timer_task": None,
        "start_task": None
    }

    builder = InlineKeyboardBuilder()
    builder.button(text="Присоединиться", callback_data="join_game")
    
    # При старте игры тоже на всякий случай чистим экран создателя от старых кнопок
    await message.answer(
        "📢 <b>Набор в игру «Слова»!</b>\n\n"
        "Жмите кнопку, чтобы участвовать.\n"
        f"Игра начнется автоматически через {config.JOIN_TIMEOUT} сек. после первого участника.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "join_game")
async def cb_join(callback: types.CallbackQuery, bot):
    chat_id = callback.message.chat.id
    user = callback.from_user
    game = games.get(chat_id)

    if not game or game['status'] != 'registration':
        await callback.answer("Уже поздно жать кнопку!", show_alert=True)
        return

    for p in game['players']:
        if p['id'] == user.id:
            await callback.answer("Ты уже в игре!", show_alert=True)
            return

    game['players'].append({
        "id": user.id,
        "name": user.full_name,
        "username": user.username or "Anon",
        "alive": True,
        "score": 0
    })
    
    await callback.message.answer(f"✅ {user.full_name} в деле! (Всего: {len(game['players'])})")
    await callback.answer()

    if len(game['players']) == 1:
        game['start_task'] = asyncio.create_task(auto_start_timer(bot, chat_id))

async def auto_start_timer(bot, chat_id):
    await asyncio.sleep(config.JOIN_TIMEOUT)
    await start_game_logic(bot, chat_id)

async def start_game_logic(bot, chat_id):
    game = games.get(chat_id)
    if not game or game['status'] != 'registration':
        return

    game['start_task'] = None

    if len(game['players']) < 2:
        await bot.send_message(chat_id, "❌ Мало игроков (нужно минимум 2). Набор отменен.")
        del games[chat_id]
        return

    game['status'] = 'running'
    
    random.shuffle(game['players'])
    game['current_player_index'] = 0
    first_player = game['players'][0]

    players_list = "\n".join([f"- {p['name']}" for p in game['players']])
    
    await bot.send_message(
        chat_id, 
        f"🚀 <b>Игра начинается!</b>\n\n"
        f"Участники:\n{players_list}\n\n"
        f"🎲 Жеребьевка...\n"
        f"👉 Первое слово задаёт <b>{first_player['name']}</b> (@{first_player['username']})!", 
        parse_mode="HTML"
    )
    
    await start_round(bot, chat_id)

@router.message(Command("stopgame"))
async def cmd_stopgame(message: types.Message):
    chat_id = message.chat.id
    game = games.get(chat_id)
    if not game: return
    
    user_id = message.from_user.id
    
    is_participant = False
    for p in game['players']:
        if p['id'] == user_id:
            is_participant = True
            break
            
    if not is_participant:
        await message.answer("⛔ Остановить игру могут только её участники!")
        return
    
    if game.get('timer_task'): game['timer_task'].cancel()
    if game.get('start_task'): game['start_task'].cancel()
    
    del games[chat_id]
    # При остановке тоже очищаем, чтобы не мешало
    await message.answer("🛑 Игра остановлена участником.", reply_markup=ReplyKeyboardRemove())

@router.message(Command("surrender"))
async def cmd_surrender(message: types.Message, bot):
    chat_id = message.chat.id
    game = games.get(chat_id)
    
    if not game or game['status'] != 'running': return

    current_player = game['players'][game['current_player_index']]
    if message.from_user.id != current_player['id']: return

    if game['timer_task']: game['timer_task'].cancel()

    current_player['alive'] = False
    await message.answer(f"🏳️ {current_player['name']} сдался.")
    
    game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
    await start_round(bot, chat_id)

@router.message(Command("top"))
async def cmd_top(message: types.Message):
    top_list = await database.get_top_players()
    if not top_list:
        await message.answer("Топ пока пуст.")
        return
        
    text = "🏆 <b>Топ игроков:</b>\n\n"
    for i, (name, score, wins) in enumerate(top_list, 1):
        text += f"{i}. <b>{name}</b>: {score} ({wins} побед)\n"
    await message.answer(text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🎮 <b>ПОЛНЫЕ ПРАВИЛА ИГРЫ «СЛОВА»</b>\n\n"
        
        "<b>📜 Как играть?</b>\n"
        "1. Создайте игру командой /startgame.\n"
        "2. Нажмите кнопку <b>«Присоединиться»</b>.\n"
        "3. Бот выберет первого игрока случайно.\n"
        "4. Пишите слово на ту букву, которой закончилось слово предыдущего игрока.\n"
        "☠️ <b>Игра идет на выбывание!</b> Кто не успел ответить за время или сдался — вылетает. Побеждает последний оставшийся.\n\n"
        
        "<b>⛔️ Важные ограничения:</b>\n"
        "• Только <b>существительные</b>, нарицательные, ед. число, Им. падеж (<i>кто? что?</i>).\n"
        "• Нельзя повторять слова, которые уже были в этом раунде.\n"
        "• Если слово заканчивается на <b>Ь, Ъ, Ы, Й</b> — следующая буква берется с конца (предпоследняя и т.д.).\n"
        "• Мат и мусорные слова бот не пропустит.\n\n"
        
        "<b>💎 Очки и таймер:</b>\n"
        f"⏳ На ход дается: <b>{config.TURN_TIMEOUT} сек.</b>\n"
        "• Короткое слово (до 5 букв): <b>+1 балл</b>\n"
        "• Среднее слово (6-8 букв): <b>+2 балла</b>\n"
        "• Длинное слово (>8 букв): <b>+3 балла</b>\n\n"
        
        "<b>🕹 Доступные команды:</b>\n"
        "/startgame — Начать новый раунд\n"
        "/surrender — Сдаться (выбыть из текущей игры)\n"
        "/top — Посмотреть таблицу лидеров\n"
        "/stopgame — Экстренно остановить игру\n"
    )
    
    # Тут тоже добавляем удаление кнопок, чтобы при вызове справки экран чистился
    await message.answer(text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
