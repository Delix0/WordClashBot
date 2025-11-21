# utils/game_logic.py
import asyncio
from aiogram import Bot
from store import games
import config
import database

async def start_round(bot: Bot, chat_id: int):
    game = games.get(chat_id)
    if not game or game['status'] != 'running':
        return

    players = game['players']
    
    # 1. Считаем ЖИВЫХ игроков
    alive_players = [p for p in players if p['alive']]
    
    # 2. Если остался 1 или 0 игроков — конец игры
    if len(alive_players) < 2:
        stats = "📊 <b>Результаты:</b>\n"
        sorted_players = sorted(players, key=lambda x: x.get('score', 0), reverse=True)
        
        winner_id = alive_players[0]['id'] if len(alive_players) == 1 else None
        winner_name = alive_players[0]['name'] if winner_id else "Никого"
        
        for p in sorted_players:
            is_winner = (p['id'] == winner_id)
            icon = "🏆" if is_winner else "▪️"
            status = "" if p['alive'] else " (выбыл)"
            stats += f"{icon} {p['name']}{status}: {p.get('score', 0)}\n"
            
            await database.update_user_stat(p['id'], p['username'], p.get('score', 0), is_winner)

        if winner_id:
            msg = f"🎉 <b>ПОБЕДА!</b> Остался только {winner_name}!\n\n{stats}"
        else:
            msg = f"🏁 Игра окончена (все выбыли).\n\n{stats}"
        
        await bot.send_message(chat_id, msg, parse_mode="HTML")
        
        if chat_id in games: del games[chat_id]
        return

    # 3. Ищем следующего живого игрока
    idx = game['current_player_index']
    start_search_idx = idx
    
    # Пропускаем выбывших
    while not players[idx]['alive']:
        idx = (idx + 1) % len(players)
        if idx == start_search_idx: break # Защита
            
    game['current_player_index'] = idx
    current_p = players[idx]

    # 4. Объявляем ход
    # Если первая буква есть — показываем её, если нет — пишем "Любая буква"
    if game['last_letter']:
        info = f"На букву: <b>{game['last_letter'].upper()}</b>"
    else:
        info = "Назови <b>любое</b> слово"
    
    await bot.send_message(
        chat_id, 
        f"⏳ <b>{current_p['name']}</b>, твой ход!\n{info} ({config.TURN_TIMEOUT} сек.)",
        parse_mode="HTML"
    )

    # Запускаем таймер
    game['timer_task'] = asyncio.create_task(turn_timer(bot, chat_id, current_p['id']))


async def turn_timer(bot: Bot, chat_id: int, player_id: int):
    try:
        await asyncio.sleep(config.TURN_TIMEOUT)
        
        game = games.get(chat_id)
        if not game: return

        current_p = game['players'][game['current_player_index']]
        if current_p['id'] != player_id:
            return

        # Тайм-аут -> вылет
        current_p['alive'] = False
        await bot.send_message(chat_id, f"💀 <b>{current_p['name']}</b> не успел и выбывает!", parse_mode="HTML")
        
        # Сдвигаем на следующего
        game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
        
        await start_round(bot, chat_id)

    except asyncio.CancelledError:
        pass

def get_next_letter(word: str) -> str:
    word = word.lower()
    for char in reversed(word):
        if char not in ['ь', 'ъ', 'ы', 'й']:
            return char
    return word[-1]