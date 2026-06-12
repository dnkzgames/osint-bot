import asyncio
import subprocess
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "8776971015:AAGYxJPoB4Pnx51UeMM6ma_5xDCG2RCA7tE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👁 OSTINeasy — OSINT по юзернейму\n\nОтправь ник для поиска:")

@dp.message()
async def search(msg: types.Message):
    username = msg.text.strip().lstrip("@")
    await msg.answer(f"🔍 Ищу @{username}...")
    
    result = subprocess.run(
        ["maigret", username, "--json", "--no-progressbar"],
        capture_output=True, text=True, timeout=60
    )
    
    try:
        data = json.loads(result.stdout)
        found = [site for site, info in data.items()