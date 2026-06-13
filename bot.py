import asyncio
import aiohttp
import base64
from aiogram import Bot, Dispatcher, F, types
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
        "📧 `/email адрес@mail.com` → поиск по email\n"
        "📸 `/photo` → отправь фото для поиска по лицу\n\n"
        "⚡ Просто отправь текст для поиска по юзернейму",
        parse_mode="Markdown"
    )

# ── /github ──────────────────────────────────────────
@dp.message(Command("github"))
async def github_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /github юзернейм")
        return

    username = parts[1].lstrip("@")
    await msg.answer(f"Ищу GitHub {username}...")

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

    lines = [f"👤 {d.get('name') or username} ({username})"]
    if d.get('bio'):              lines.append(f"📝 {d['bio']}")
    if d.get('company'):          lines.append(f"🏢 {d['company']}")
    if d.get('location'):         lines.append(f"📍 {d['location']}")
    if d.get('email'):            lines.append(f"📧 {d['email']}")
    if d.get('blog'):             lines.append(f"🌐 {d['blog']}")
    if d.get('twitter_username'): lines.append(f"🐦 @{d['twitter_username']}")
    lines.append(f"\nРепо: {d.get('public_repos',0)} | Подписчиков: {d.get('followers',0)} | Подписок: {d.get('following',0)}")
    lines.append(f"Регистрация: {str(d.get('created_at',''))[:10]}")

    if repos and isinstance(repos, list):
        lines.append("\nПоследние репозитории:")
        for repo in repos[:3]:
            lines.append(f"• {repo['name']} ⭐{repo.get('stargazers_count',0)} ({repo.get('language') or '—'})")
            lines.append(f"  {repo['html_url']}")

    if events and isinstance(events, list):
        push_events = [e for e in events if e.get('type') == 'PushEvent']
        if push_events:
            commits = push_events[0].get('payload', {}).get('commits', [])
            if commits:
                email = commits[0].get('author', {}).get('email', '')
                if email and 'noreply' not in email:
                    lines.append(f"\nEmail из коммитов: {email}")

    lines.append(f"\nhttps://github.com/{username}")
    await msg.answer("\n".join(lines))

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
                params={"apikey": "num_live_57lWbtzfCnCwioailOivkoGDKicMGgh3V97o75iI"},
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

# ── /photo ───────────────────────────────────────────
@dp.message(Command("photo"))
async def photo_cmd(msg: types.Message):
    await msg.answer(
        "📸 Отправь фото с лицом — поищу по интернету через PimEyes.\n"
        "⚠️ Работает нестабильно, бесплатный лимит ограничен."
    )

# ── Обработка фото ───────────────────────────────────
@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    await msg.answer("🔍 Ищу лицо по базам...")

    file = await bot.get_file(msg.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    b64 = base64.b64encode(photo_bytes.read()).decode()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://pimeyes.com",
        "Referer": "https://pimeyes.com/",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as s:
        try:
            # Получаем cookies и CSRF
            await s.get("https://pimeyes.com", timeout=aiohttp.ClientTimeout(total=8))

            payload = f'"data:image/jpeg;base64,{b64}"'
            async with s.post(
                "https://pimeyes.com/api/upload/file",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as r:
                text_resp = await r.text()
                if r.content_type == 'application/json' or '{' in text_resp:
                    import json
                    data = json.loads(text_resp)
                    faces = data.get("faces", [])

                    if faces:
                        result = f"✅ Найдено совпадений: {len(faces)}\n\n"
                        for face in faces[:5]:
                            result += f"• {face.get('url', '')}\n"
                        if len(faces) > 5:
                            result += f"...и ещё {len(faces)-5}"
                    else:
                        result = "❌ Совпадений не найдено (лимит или лицо не распознано)"
                else:
                    result = "⚠️ PimEyes требует авторизацию или сменил API. Попробуй позже."

        except Exception as e:
            result = f"⚠️ Ошибка: {str(e)[:150]}"

    await msg.answer(result)
# ── Запуск ────────────────────────────────────────────
async def main():
    await load_sites()
    await dp.start_polling(bot)

asyncio.run(main())