import asyncio
import aiohttp
import base64
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8776971015:AAGYxJPoB4Pnx51UeMM6ma_5xDCG2RCA7tE"
GITHUB_TOKEN = "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"
NUMLOOKUP_KEY = "num_live_57lWbtzfCnCwioailOivkoGDKicMGgh3V97o75iI"
WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
wmn_sites = []


# ── Заголовки для GitHub API (с PAT — лимит 5000/час вместо 60) ──
def gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


# ── Inline-меню ──────────────────────────────────────
def main_menu() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Юзернейм",        callback_data="menu:username")
    kb.button(text="👤 GitHub",          callback_data="menu:github")
    kb.button(text="📧 Email из коммитов", callback_data="menu:gitemail")
    kb.button(text="📱 Телефон",         callback_data="menu:phone")
    kb.button(text="✉️ Email",           callback_data="menu:email")
    kb.button(text="📸 Фото",            callback_data="menu:photo")
    kb.adjust(2)
    return kb.as_markup()


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
        "📧 /gitemail юзернейм — email из коммитов GitHub\n"
        "📱 /phone +77001234567 — инфо о номере\n"
        "✉️ /email адрес@mail.com — поиск по email\n"
        "📸 /photo — затем отправь фото для реверс-поиска\n\n"
        "Или жми кнопки ниже 👇"
    )
    await msg.answer(text, reply_markup=main_menu())


# ── Роутер inline-кнопок ─────────────────────────────
@dp.callback_query(F.data.startswith("menu:"))
async def menu_router(cb: types.CallbackQuery):
    prompts = {
        "username": "🔍 Отправь ник — ищу по 500+ сайтам.",
        "github":   "👤 Введи: /github юзернейм",
        "gitemail": "📧 Введи: /gitemail юзернейм — выкопаю email из коммитов.",
        "phone":    "📱 Введи: /phone +77001234567",
        "email":    "✉️ Введи: /email адрес@mail.com",
        "photo":    "📸 Отправь фото без подписи — дам ссылки на реверс-поиск.",
    }
    action = cb.data.split(":", 1)[1]
    await cb.message.answer(prompts.get(action, "Неизвестная команда"))
    await cb.answer()


# ── /github (с PAT-токеном) ──────────────────────────
@dp.message(Command("github"))
async def github_lookup(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /github юзернейм")
        return

    username = parts[1].lstrip("@")
    await msg.answer(f"Ищу GitHub {username}...")

    async with aiohttp.ClientSession(headers=gh_headers()) as s:
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


# ── /gitemail (глубокий поиск email по коммитам) ─────
@dp.message(Command("gitemail"))
async def gitemail(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /gitemail юзернейм")
        return

    username = parts[1].lstrip("@")
    await msg.answer(f"📧 Копаю коммиты {username}... может занять время")

    emails: dict[str, set[str]] = {}
    async with aiohttp.ClientSession(headers=gh_headers()) as s:
        # список репозиториев (свежие — первыми)
        async with s.get(
            f"https://api.github.com/users/{username}/repos?per_page=100&sort=pushed"
        ) as r:
            if r.status != 200:
                await msg.answer("❌ Не удалось получить репозитории")
                return
            repos = await r.json()

        if not isinstance(repos, list) or not repos:
            await msg.answer("❌ У пользователя нет публичных репозиториев")
            return

        # ограничиваем 20 репами, чтобы не выжечь лимит даже с PAT
        for repo in repos[:20]:
            name = repo.get("name")
            if not name:
                continue
            url = f"https://api.github.com/repos/{username}/{name}/commits?per_page=30"
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        continue
                    commits = await r.json()
            except:
                continue

            if not isinstance(commits, list):
                continue

            for c in commits:
                commit = c.get("commit", {})
                for role in ("author", "committer"):
                    person = commit.get(role, {})
                    email = person.get("email", "")
                    pname = person.get("name", "")
                    if email and "noreply" not in email:
                        emails.setdefault(email, set()).add(pname)

    if not emails:
        await msg.answer("❌ Реальных email в коммитах не найдено (всё скрыто noreply)")
        return

    lines = [f"📧 Email из коммитов {username}:\n"]
    for email, names in emails.items():
        tag = ", ".join(n for n in names if n)
        lines.append(f"• {email}" + (f"  ({tag})" if tag else ""))
    lines.append(f"\nВсего адресов: {len(emails)}")
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
                params={"apikey": NUMLOOKUP_KEY},
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
                item = result[0]
                image_url = "https://telegra.ph" + (item["src"] if isinstance(item, dict) else item)

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