import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "8776971015:AAGYxJPoB4Pnx51UeMM6ma_5xDCG2RCA7tE"
WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
wmn_sites = []

# ── Загрузка базы сайтов ─────────────────────────────
async def load_sites():
    global wmn_sites
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(WMN_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                wmn_sites = data.get("sites", [])
        print(f"✅ Загружено {len(wmn_sites)} сайтов")
    except Exception as e:
        print(f"❌ Ошибка загрузки базы: {e}")

# ── Проверка одного сайта ────────────────────────────
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

# ── Поиск юзернейма ──────────────────────────────────
async def check_username(username: str) -> list:
    sem = asyncio.Semaphore(30)
    async with aiohttp.ClientSession() as session:
        tasks = [check_site(session, sem, site, username) for site in wmn_sites]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r]

# ── /start ───────────────────────────────────────────
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "👁 *OSTINeasy* — OSINT бот\n\n"
        "🔍 *Юзернейм* — отправь ник → поиск по 500+ сайтам\n"
        "👤 `/github юзернейм` → детали GitHub профиля\n"
        "📱 `/phone +77001234567` → инфо о номере\n"
        "📧 `/email адрес@mail.com` → поиск по email\n\n"
        "⚡ Просто отправь текст для поиска по юзернейму",
        parse_mode="Markdown"
    )

# ── /github ──────────────────────────────────────────
@dp.message(Command("github"))
async def github_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/github юзернейм`", parse_mode="Markdown")
        return

    username = parts[1].lstrip("@")
    await msg.answer(f"🔍 Ищу GitHub `{username}`...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://api.github.com/users/{username}") as r:
            if r.status != 200:
                await msg.answer("❌ Пользователь не найден")
                return
            d = await r.json()

        async with s.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3"
        ) as r:
            repos = await r.json() if r.status == 200 else []

        async with s.get(
            f"https://api.github.com/users/{username}/events/public?per_page=5"
        ) as r:
            events = await r.json() if r.status == 200 else []

    text = f"👤 *{d.get('name') or username}* (`{username}`)\n"
    if d.get('bio'):              text += f"📝 _{d['bio']}_\n"
    if d.get('company'):          text += f"🏢 {d['company']}\n"
    if d.get('location'):         text += f"📍 {d['location']}\n"
    if d.get('email'):            text += f"📧 `{d['email']}`\n"
    if d.get('blog'):             text += f"🌐 {d['blog']}\n"
    if d.get('twitter_username'): text += f"🐦 @{d['twitter_username']}\n"

    text += (
        f"\n📊 *Статистика:*\n"
        f"• Репозиториев: {d.get('public_repos', 0)}\n"
        f"• Подписчиков: {d.get('followers', 0)}\n"
        f"• Подписок: {d.get('following', 0)}\n"
        f"• Дата регистрации: {str(d.get('created_at', ''))[:10]}\n"
    )

    if repos and isinstance(repos, list):
        text += "\n📦 *Последние репозитории:*\n"
        for repo in repos[:3]:
            stars = repo.get('stargazers_count', 0)
            lang = repo.get('language') or '—'
            text += f"• [{repo['name']}]({repo['html_url']}) ⭐{stars} `{lang}`\n"

    if events and isinstance(events, list):
        push_events = [e for e in events if e.get('type') == 'PushEvent']
        if push_events:
            last = push_events[0]
            commits = last.get('payload', {}).get('commits', [])
            if commits:
                commit_email = commits[0].get('author', {}).get('email', '')
                if commit_email and 'noreply' not in commit_email:
                    text += f"\n📧 *Email из коммитов:* `{commit_email}`\n"

    text += f"\n🔗 [Открыть профиль](https://github.com/{username})"
    await msg.answer(text, parse_mode="Markdown")

# ── /phone ───────────────────────────────────────────
@dp.message(Command("phone"))
async def phone_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/phone +77001234567`", parse_mode="Markdown")
        return

    number = parts[1]
    await msg.answer(f"📱 Ищу `{number}`...", parse_mode="Markdown")
    results = []

    # NumLookup
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(
                f"https://api.numlookupapi.com/v1/info/{number}",
                params={"apikey": "demo"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    if d.get('country_name'): results.append(f"🌍 Страна: {d['country_name']}")
                    if d.get('carrier'):      results.append(f"📡 Оператор: {d['carrier']}")
                    if d.get('line_type'):    results.append(f"📞 Тип: {d['line_type']}")
        except:
            pass

    # TrueCaller
    async with aiohttp.ClientSession() as s:
        try:
            headers = {
                "Authorization": "Bearer c2d85ef4-2d15-11e9-a1d5-0a3a88c8f4b7",
                "Content-Type": "application/json; charset=UTF-8"
            }
            async with s.get(
                f"https://search5-noneu.truecaller.com/v2/search"
                f"?q={number}&countryCode=KZ&type=4",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    data = d.get("data", [])
                    if data:
                        name = data[0].get("name", "")
                        if name: results.append(f"👤 Имя (TrueCaller): *{name}*")
                        score = data[0].get("spamScore", 0)
                        if score > 0: results.append(f"⚠️ Спам-рейтинг: {score}")
        except:
            pass

    if results:
        text = f"📱 *{number}*\n\n" + "\n".join(results)
    else:
        text = "❌ Информация не найдена. Проверь формат: +77001234567"

    await msg.answer(text, parse_mode="Markdown")

# ── /email ───────────────────────────────────────────
@dp.message(Command("email"))
async def email_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: `/email адрес@mail.com`", parse_mode="Markdown")
        return

    email = parts[1]
    await msg.answer(
        f"📧 *{email}*\n\n"
        f"🔍 Проверь вручную:\n"
        f"• [Epieos](https://epieos.com/?q={email}) — Google аккаунт, соцсети\n"
        f"• [HaveIBeenPwned](https://haveibeenpwned.com/account/{email}) — утечки\n"
        f"• [Hunter.io](https://hunter.io/email-finder) — корпоративные email",
        parse_mode="Markdown"
    )

# ── Username search ───────────────────────────────────
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
        text += "\n".join(f"• [{site}]({url})" for site, url in found[:35])
        if len(found) > 35:
            text += f"\n\n_...и ещё {len(found) - 35} сайтов_"
    else:
        text = "❌ Ничего не найдено"

    await msg.answer(text, parse_mode="Markdown")

# ── Запуск ────────────────────────────────────────────
async def main():
    await load_sites()
    await dp.start_polling(bot)

asyncio.run(main())