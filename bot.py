import asyncio
import aiohttp
import base64
import json
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
    text = (
        "👁 OSTINeasy — OSINT бот\n\n"
        "🔍 Юзернейм — отправь ник, поиск по 500+ сайтам\n"
        "👤 /github юзернейм — детали GitHub профиля\n"
        "📱 /phone +77001234567 — инфо о номере\n"
        "📧 /email адрес@mail.com — поиск по email\n"
        "📸 /photo — затем отправь фото для реверс-поиска\n\n"
        "Просто отправь текст для поиска по юзернейму."
    )
    await msg.answer(text)

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

    lines.append("")
    lines.append(f"Репозиториев: {d.get('public_repos', 0)}")
    lines.append(f"Подписчиков: {d.get('followers', 0)}")
    lines.append(f"Подписок: {d.get('following', 0)}")
    lines.append(f"Регистрация: {str(d.get('created_at', ''))[:10]}")

    if repos and isinstance(repos, list):
        lines.append("\nПоследние репозитории:")
        for repo in repos[:3]:
            lang = repo.get('language') or '—'
            stars = repo.get('stargazers_count', 0)
            lines.append(f"• {repo['name']} | ⭐{stars} | {lang}")
            lines.append(f"  {repo['html_url']}")

    if events and isinstance(events, list):
        push_events = [e for e in events if e.get('type') == 'PushEvent']
        if push_events:
            commits = push_events[0].get('payload', {}).get('commits', [])
            if commits:
                commit_email = commits[0].get('author', {}).get('email', '')
                if commit_email and 'noreply' not in commit_email:
                    lines.append(f"\nEmail из коммитов: {commit_email}")

    lines.append(f"\nhttps://github.com/{username}")
    await msg.answer("\n".join(lines))

# ── /phone ───────────────────────────────────────────
@dp.message(Command("phone"))
async def phone_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /phone +77001234567")
        return

    number = parts[1]
    await msg.answer(f"Ищу {number}...")
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
                f"https://search5-noneu.truecaller.com/v2/search?q={number}&countryCode=KZ&type=4",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    data = d.get("data", [])
                    if data:
                        name = data[0].get("name", "")
                        if name: results.append(f"👤 Имя (TrueCaller): {name}")
                        score = data[0].get("spamScore", 0)
                        if score > 0: results.append(f"⚠️ Спам-рейтинг: {score}")
        except:
            pass

    if results:
        text = f"📱 {number}\n\n" + "\n".join(results)
    else:
        text = "❌ Информация не найдена. Проверь формат: +77001234567"

    await msg.answer(text)

# ── /email ───────────────────────────────────────────
@dp.message(Command("email"))
async def email_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /email адрес@mail.com")
        return

    email = parts[1]
    text = (
        f"📧 {email}\n\n"
        f"Проверь вручную:\n"
        f"• Epieos (Google аккаунт): https://epieos.com/?q={email}\n"
        f"• HaveIBeenPwned (утечки): https://haveibeenpwned.com/account/{email}\n"
        f"• Hunter.io (корп. email): https://hunter.io/email-finder"
    )
    await msg.answer(text)

# ── /photo ───────────────────────────────────────────
@dp.message(Command("photo"))
async def photo_cmd(msg: types.Message):
    await msg.answer(
        "📸 Отправь фото без подписи — загружу и дам ссылки на реверс-поиск.\n"
        "Яндекс лучше всего находит людей из СНГ."
    )

# ── Обработка фото ───────────────────────────────────
@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    await msg.answer("📸 Загружаю фото...")

    file = await bot.get_file(msg.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    image_data = photo_bytes.read()

    async with aiohttp.ClientSession() as s:
        try:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                image_data,
                filename="photo.jpg",
                content_type="image/jpeg"
            )
            async with s.post(
                "https://telegra.ph/upload",
                data=form,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                result = await r.json()
                image_url = "https://telegra.ph" + result[0]["src"]

            yandex = f"https://yandex.ru/images/search?rpt=imageview&url={image_url}"
            google = f"https://lens.google.com/uploadbyurl?url={image_url}"
            tineye = f"https://tineye.com/search?url={image_url}"

            text = (
                f"✅ Фото загружено. Ссылки для поиска:\n\n"
                f"🔍 Яндекс Картинки:\n{yandex}\n\n"
                f"🔍 Google Lens:\n{google}\n\n"
                f"🔍 TinEye:\n{tineye}"
            )

        except Exception as e:
            text = f"⚠️ Ошибка: {str(e)[:150]}"

    await msg.answer(text)

# ── Username search ───────────────────────────────────
@dp.message()
async def search(msg: types.Message):
    username = msg.text.strip().lstrip("@")
    if not username or len(username) < 2:
        return

    count = len(wmn_sites)
    await msg.answer(f"🔍 Ищу @{username} по {count} сайтам... (~20 сек)")

    found = await check_username(username)

    if found:
        lines = [f"✅ Найден на {len(found)} платформах:\n"]
        for site, url in found[:35]:
            lines.append(f"• {site}: {url}")
        if len(found) > 35:
            lines.append(f"\n...и ещё {len(found) - 35} сайтов")
        text = "\n".join(lines)
    else:
        text = "❌ Ничего не найдено"

    await msg.answer(text)

# ── Запуск ────────────────────────────────────────────
async def main():
    await load_sites()
    await dp.start_polling(bot)

asyncio.run(main())