import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "твой_токен"

SITES = {
    "GitHub": "https://github.com/{}",
    "Twitter": "https://twitter.com/{}",
    "Instagram": "https://www.instagram.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "VK": "https://vk.com/{}",
    "Telegram": "https://t.me/{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Pinterest": "https://www.pinterest.com/{}",
    "Twitch": "https://www.twitch.tv/{}",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_username(username: str) -> list:
    found = []
    async with aiohttp.ClientSession() as session:
        for site, url_template in SITES.items():
            url = url_template.format(username)
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True
                ) as resp:
                    if resp.status == 200:
                        found.append((site, url))
            except:
                pass
    return found

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👁 OSTINeasy\n\nОтправь юзернейм для поиска:")

@dp.message()
async def search(msg: types.Message):
    username = msg.text.strip().lstrip("@")
    await msg.answer(f"🔍 Ищу @{username}...")
    found = await check_username(username)
    if found:
        text = f"✅ Найден на {len(found)} платформах:\n\n"
        text += "\n".join(f"• [{site}]({url})" for site, url in found)
    else:
        text = "❌ Ничего не найдено"
    await msg.answer(text, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

asyncio.run(main())