# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import management, gameplay

import database # Инициализация базы данных при старте

# Включаем логирование, чтобы видеть ошибки
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация бота и диспетчера
    await database.init_db()
    bot = Bot(token=config.TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров (handlers)
    # Важен порядок: сначала специфичные команды, потом общий перехватчик сообщений
    dp.include_router(management.router)
    dp.include_router(gameplay.router)

    # Удаляем вебхуки и запускаем пулинг
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")