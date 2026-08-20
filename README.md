# Moira — ИИ-оракул таро (Telegram-бот)

Двуязычный (RU/EN) Telegram-бот: таро-расклады с ИИ-трактовками, картинки карт,
голосовые предсказания, личный алтарь с картой дня и лунным календарём,
тест «Мой Аркан». Монетизация: Telegram Stars + промокоды.

## Что работает и проверено

- 🃏 **Расклады «Ситуация / Любовь / Выбор»**: картинка расклада + текстовая
  трактовка под Telegram-spoiler; голос оракула остаётся экспериментальной
  capability до отдельной live-приёмки.
- 🔮 **ИИ-трактовки**: OpenAI-compatible endpoint (OpenRouter/AIGate/другой);
  без ключа — встроенные трактовки карт. Структурированный вывод через Instructor
  с лимитами длины, safety-фильтром и одним retry.
- 🌙 **Личный алтарь**: карта дня, фаза Луны, Луна в знаке, персональная строка
  по стихиям (если указана дата рождения). Утренний пуш (06 UTC ≈ 09 МСК).
- 🎭 **Тест «Мой Аркан»**: 6 вопросов → Старший Аркан с картинкой и девизом.
- 💎 **Тарифы Stars**: 1 расклад 25⭐ / 7 дней 99⭐ / 30 дней 150⭐ (подписка).
- 🎟 **Промокоды** и early-bird (первым 50 пользователям +3 расклада).
- 🌐 **RU/EN**: автоопределение языка + переключатель.
- 👑 **Админка**: `/stats`, `/promo_create`, `/promo_list`, `/grant`.
- 💰 **Платежи**: idempotent payment ledger по `telegram_payment_charge_id`,
  атомарная выдача прав, referral reward один раз, self-referral запрещён,
  обработка refund.
- 🗑 **Удаление данных**: `/delete_my_data` удаляет расклады, избранное,
  события, usage-записи и профиль. Payment-ledger остаётся для аудита.
- 🔒 **Приватность**: Sentry/PostHog не получают вопросы, трактовки, имена,
  usernames, даты рождения и Telegram ID в открытом виде.
- 📖 **Дневник раскладов**: открывает сохранённый вопрос, карты и трактовку;
  из записи доступны избранное, безопасный share, контекстное продолжение и
  feedback 👍/👎.

## Реализовано, но экспериментально

- 🪞 **Зеркало недели**: воскресное резюме по частым картам за неделю.
  Работает, но качество LLM-резюме зависит от модели.
- 🎤 **Голос**: edge-tts озвучивает краткий результат. Опциональный Deepgram
  voice-to-question flow принимает короткое голосовое, показывает редактируемый
  текст и запускает тот же расклад только после подтверждения пользователя. Для
  включения нужны `DEEPGRAM_API_KEY` и `DEEPGRAM_STT_ENABLED=true`; rollout и
  pilot gates — в `docs/DEEPGRAM_VOICE_POC.md`.
- 🌟 **Реферальная программа**: ссылка `https://t.me/<bot>?start=ref_<id>`,
  награда за первый платёж приглашённого. Проверка подписки на канал пока не
  реализована.

## Growth-pilot: share → referral → first reading

Каждая share-карточка получает стабильный вариант caption A или B и передаёт
вариант в referral deep link. События хранят только псевдонимный идентификатор,
вариант и этап воронки — без вопроса, имени или Telegram ID. После feedback
бот сразу предлагает два контекстных follow-up действия, поэтому пользователь
может продолжить расклад одним нажатием.

После запуска invite-only пилота собери первые 20 attributed referral signups:

```powershell
.venv\Scripts\python.exe scripts\growth_pilot_report.py --min-signups 20
```

Сравни A и B сначала по `signup_per_share`, затем по `reading_per_signup`.
Не меняй вариант во время сбора — иначе воронка станет несопоставимой.

## Известные ограничения

- **SQLite**: один writer-процесс. Не запускайте несколько инстансов бота
  с одной БД одновременно.
- **Фоновые задачи** (daily push / weekly mirror) живут в процессе polling.
  При рестарте планировщик начинает заново; дубли предотвращаются полями
  `last_push_date` и `last_mirror_week`.
- **TTS**: edge-tts требует интернета и возвращает MP3. Telegram voice note
  предпочитает OGG/OPUS; текущая реализация полагается на Bot API.
- **Safety**: фильтр чувствительных тем — эвристический. Он снижает риск, но
  не заменяет человеческую модерацию.
- **Визуал**: рендер карт требует файлов из `assets/cards/`. Если карта или шрифт
  отсутствуют, бот продолжает работу, но изображение будет неполным.

## Запланировано

- ЮKassa (карты РФ/СБП) для внешнего платёжного сценария.
- Натальная карта и расширенная астрология.
- Webhook-режим и отдельный worker для фоновых задач.
- PostgreSQL при росте нагрузки.

## Визуальная система

Рендер изображений (расклад, share-карточка, карта дня, алтарь, результат
«Мой Аркан») построен на едином дизайн-реестре `bot/visual/tokens.py`:
цвета, шрифты, canvas-размеры (1080×1500 — расклад, 1080×1080 — share,
1080×1350 — карта дня/алтарь/quiz), кегли, отступы, радиусы и декоративные
параметры. В функциях Pillow (`bot/visual/render.py`) нет магических чисел.

**Шрифт**: PT Serif Regular/Bold — SIL Open Font License 1.1
(© ParaType Ltd., 2010), файлы в `assets/fonts/`, покрытие кириллицы и латиницы.
Порядок выбора шрифта: project-local → системные fallback →
`ImageFont.load_default()` (только аварийно). Неподдерживаемые глифы (эмодзи,
✦, ⟲) удаляются санитайзером при отрисовке; маркер перевёрнутой карты —
локализованный текст (RU/EN).

**Галерея и ревью**: 16 проверенных сценариев в `artifacts/visual_review/`,
подробный разбор в `docs/VISUAL_REVIEW.md`.

## Запуск (локально, Windows)

1. У @BotFather: `/newbot` → получить токен.
2. Скопируй `.env.example` → `.env`, вставь `BOT_TOKEN` и `ADMIN_IDS`.
3. Установи зависимости (один раз):
   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```
4. Накати миграции:
   ```powershell
   .venv\Scripts\python.exe -m alembic upgrade head
   .venv\Scripts\python.exe -m alembic check
   ```
5. Запуск:
   ```powershell
   run.bat
   # или
   .venv\Scripts\python.exe -m bot.main
   ```

## Запуск (Linux / VPS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
alembic check
python -m bot.main
```

## Миграции БД (Alembic)

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic check
```

Текущая версия: `0009_llm_usage_privacy`. Запуск приложения требует,
чтобы база уже находилась на этом Alembic head; `create_all()` не заменяет
миграции. Сначала всегда выполняй `alembic upgrade head` и `alembic check`.

Перед любыми миграциями на production:

```powershell
cp moira.db moira.db.$(Get-Date -Format yyyyMMdd-HHmmss).bak
```

## Подключение ИИ-трактовок

```env
OPENROUTER_API_KEY=sk-or-...
# или любой OpenAI-compatible endpoint:
LLM_BASE_URL=https://api.aigate.shop/v1
LLM_MODEL=deepseek/deepseek-v4-flash
```

Для нативного API DeepSeek используй `LLM_BASE_URL=https://api.deepseek.com` и
`LLM_MODEL=deepseek-v4-flash` (без префикса провайдера). Для шлюзов с каталогом
моделей модель остаётся `deepseek/deepseek-v4-flash`.

Для Mistral оставь `OPENROUTER_API_KEY` пустым и используй внешний secret-файл,
который содержит только ключ:

```env
OPENROUTER_API_KEY=
LLM_API_KEY_FILE=C:\secure\mistral-api-key.txt
LLM_BASE_URL=https://api.mistral.ai/v1
LLM_MODEL=mistral-small-latest
LLM_JSON_MODE=true
```

Secret-файл должен находиться вне репозитория и не включаться в release
artifacts. Governing provider evaluation использует только синтетическую
24-case fixture; реальные вопросы пользователей не являются test data.

Без ключа бот работает на встроенных трактовках карт (режим MVP).

Release-default feature flags остаются закрытыми до независимых gates:

```env
LLM_RETRY_POLICY_V2=false
LLM_CONTROLLED_REPAIR_ENABLED=false
DEEPGRAM_STT_ENABLED=false
```

TTS и Telegram Stars нельзя считать production-enabled только по наличию кода:
для них требуются отдельные live capability gates из production roadmap.

## Команды

```
/start          — меню и онбординг
/help           — помощь
/delete_my_data — удалить свои данные
```

Админ:

```
/stats
/promo_create readings 5 WELCOME5
/promo_create days 30 VIP30
/promo_list
/grant 123456789 readings:3
```

## Тесты

```powershell
.venv\Scripts\python.exe -m compileall bot
.venv\Scripts\python.exe tests/smoke_test.py
.venv\Scripts\python.exe tests/test_patch1_runtime.py
.venv\Scripts\python.exe tests/test_patch2_payments.py
.venv\Scripts\python.exe tests/test_patch3_llm.py
.venv\Scripts\python.exe tests/test_patch4_critical.py
.venv\Scripts\python.exe tests/test_patch5_i18n_quiz.py
.venv\Scripts\python.exe tests/test_patch6_background.py
```

## Privacy и безопасность

- Тексты вопросов и трактовок не уходят в Sentry/PostHog.
- `OPENROUTER_API_KEY`, `BOT_TOKEN`, `SENTRY_DSN`, `POSTHOG_API_KEY` не логируются.
- Пользователь может удалить свои данные через `/delete_my_data`.
- Бот отказывает в трактовке медицинских, юридических, финансовых и кризисных
  запросов, а также попыток prompt injection.

## Лицензия и карты

- Код проекта — собственная разработка.
- Изображения карт — полный RWS public-domain set из Wikimedia Commons,
  78/78 tracked в assets/cards/. Локальные и исходные хэши:
  [assets/cards/PROVENANCE.md](assets/cards/PROVENANCE.md).

## Runbooks

- Invite-only beta: [docs/BETA_RUNBOOK.md](docs/BETA_RUNBOOK.md)
- Single-instance production: [docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md)
- Product decisions informed by Sibyl research: [docs/SIBYL_PRODUCT_COMPARISON.md](docs/SIBYL_PRODUCT_COMPARISON.md)

## Deployment source policy

Развёртывается только exact commit SHA, для которого завершились terminal CI
gates и совпали sanitized artifact manifest и reviewed Candidate manifest.
Локальные ветки, dirty snapshots и старое имя `v6-rc2` не являются доступным
release source. До подтверждённой ротации ранее скомпрометированного GitHub
credential push запрещён; remote URL не должен содержать userinfo или token.
