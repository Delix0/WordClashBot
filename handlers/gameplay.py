# handlers/gameplay.py
from aiogram import Router, types
from store import games
from utils.game_logic import get_next_letter, start_round
from utils.dictionary import check_word

router = Router()

@router.message()
async def game_message_handler(message: types.Message, bot):
    chat_id = message.chat.id
    game = games.get(chat_id)

    if not game or game['status'] != 'running':
        return
    
    current_player = game['players'][game['current_player_index']]
    if message.from_user.id != current_player['id']:
        return

    text = message.text.strip().lower()
    
    if len(text.split()) > 1 or not text.isalpha():
        await message.reply("⚠️ Пиши только одно слово (без цифр и пробелов).")
        return

    required_char = game['last_letter']
    if required_char and not text.startswith(required_char):
        await message.reply(f"⚠️ Слово должно начинаться на букву <b>{required_char.upper()}</b>!", parse_mode="HTML")
        return

    if text in game['used_words']:
        await message.reply("⚠️ Это слово уже называли!")
        return

    check_result = check_word(text)
    if not check_result['valid']:
        await message.reply(check_result['error'], parse_mode="HTML")
        return

    # --- ХОД ПРИНЯТ ---
    
    if game['timer_task']:
        game['timer_task'].cancel()

    game['used_words'].add(text)
    game['last_letter'] = get_next_letter(text)
    
    word_len = len(text)
    points = 1
    if word_len > 5: points += 1
    if word_len > 8: points += 2
    
    current_player['score'] = current_player.get('score', 0) + points
    
    await message.answer(
        f"✅ <b>{text.title()}</b> принято! (+{points} б.)\n"
        f"Следующая буква: <b>{game['last_letter'].upper()}</b>",
        parse_mode="HTML"
    )
    
    game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
    
    await start_round(bot, chat_id)