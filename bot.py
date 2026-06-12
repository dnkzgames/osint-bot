import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "8776971015:AAGYxJPoB4Pnx51UeMM6ma_5xDCG2RCA7tE"
WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
wmn_sites = []

async def load_sites():
    global wmn_sites
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(WMN_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                wmn_sites = data.get("sites", [])
    except:
        wmn_sites = []

async def check_site(session, sem, site, username):
    url = site["uri_check"].replace("{account}", username)
    try:
        async with sem:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True,
                ssl=False
            ) as resp:
                if resp.status == site.get("e_code", 200):
                    return (site["name"], url)
    except:
        pass
    return None

async def check_username(username: str) -> list:
    sem = asyncio.Semaphore(30)
    async with aiohttp.ClientSession() as session:
        tasks = [check_site(session, sem, site, username) for site in wmn_sites]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r]

# ── /start ──────────────────────────────────────────
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "👁 *OSTINeasy* — OSINT бот\n\n"
        "🔍 Отправь *юзернейм* → поиск по 500+ сайтам\n"
        "📧 `/email адрес` → проверка email\n"
        "👤 `/github юзернейм` → детали профиля\n"
        "📱 `/phone +77001234567` → инфо о номере",
        parse_mode="Markdown"
    )

# ── /github ─────────────────────────────────────────
@dp.message(Command("github"))
async def github_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/github юзернейм`", parse_mode="Markdown")
        return
    username = parts[1].lstrip("@")
    await msg.answer(f"🔍 Ищу GitHub `{username}`...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as s:
        # Профиль
        async with s.get(f"https://api.github.com/users/{username}") as r:
            if r.status != 200:
                await msg.answer("❌ Пользователь не найден")
                return
            d = await r.json()

        # Последние репозитории
        async with s.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3") as r:
            repos = await r.json() if r.status == 200 else []

    text = f"👤 *{d.get('name') or username}* (`{username}`)\n"
    if d.get('bio'):        text += f"📝 _{d['bio']}_\n"
    if d.get('company'):    text += f"🏢 {d['company']}\n"
    if d.get('location'):   text += f"📍 {d['location']}\n"
    if d.get('email'):      text += f"📧 `{d['email']}`\n"
    if d.get('blog'):       text += f"🌐 {d['blog']}\n"
    if d.get('twitter_username'): text += f"🐦 @{d['twitter_username']}\n"

    text += (
        f"\n⭐ Репо: {d.get('public_repos',0)} | "
        f"👥 Подписчиков: {d.get('followers',0)} | "
        f"➡️ Подписок: {d.get('following',0)}\n"
        f"📅 Регистрация: {str(d.get('created_at',''))[:10]}\n"
    )

    if repos and isinstance(repos, list):
        text += "\n📦 *Последние репозитории:*\n"
        for repo in repos[:3]:
            stars = repo.get('stargazers_count', 0)
            text += f"• [{repo['name']}]({repo['html_url']}) ⭐{stars}\n"

    text += f"\n🔗 [Открыть профиль](https://github.com/{username})"
    await msg.answer(text, parse_mode="Markdown")

# ── /phone ──────────────────────────────────────────
@dp.message(Command("phone"))
async def phone_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/phone +77001234567`", parse_mode="Markdown")
        return
    number = parts[1]
    await msg.answer(f"📱 Ищу `{number}`...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://api.numlookupapi.com/v1/info/{number}",
            params={"apikey": "demo"}
        ) as r:
            if r.status == 200:
                d = await r.json()
                text = f"📱 *{number}*\n\n"
                if d.get('country_name'): text += f"🌍 Страна: {d['country_name']}\n"
                if d.get('carrier'):      text += f"📡 Оператор: {d['carrier']}\n"
                if d.get('line_type'):    text += f"📞 Тип линии: {d['line_type']}\n"
                if d.get('valid') is False: text += "⚠️ Номер невалиден\n"
                await msg.answer(text, parse_mode="Markdown")
            else:
                await msg.answer("❌ Не удалось найти инфо. Попробуй формат: +77001234567")

# ── /email ──────────────────────────────────────────
@dp.message(Command("email"))
async def email_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/email адрес@mail.com`", parse_mode="Markdown")
        return
    email = parts[1]
    await msg.answer(
        f"📧 *{email}*\n\n"
        "⚠️ Поиск по email в разработке.\n"
        "Пока используй: [epieos.com](https://epieos.com) — вставь email вручную.",
        parse_mode="Markdown"
    )

# ── Username search ──────────────────────────────────
@dp.message()
async def search(msg: types.Message):
    username = msg.text.strip().lstrip("@")
    if not username or len(username) < 2:
        return
    count = len(wmn_sites)
    await msg.answer(
        f"🔍 Ищу *@{username}* по {count} сайтам...\n⏳ ~20 секунд",
        parse_mode="Markdown"
    )
    found = await check_username(username)
    if found:
        text = f"✅ Найден на *{len(found)}* платформах:\n\n"
        lines = [f"• [{site}]({url})" for site, url in found[:35]]
        text += "\n".join(lines)
        if len(found) > 35:
            text += f"\n_...и ещё {len(found)-35} сайтов_"
    else:
        text = "❌ Ничего не найдено"
    await msg.answer(text, parse_mode="Markdown")

async def main():
    print("Загружаю базу сайтов...")
    await load_sites()
    print(f"Загружено {len(wmn_sites)} сайтов. Бот запущен.")
    await dp.start_polling(bot)

asyncio.run(main())