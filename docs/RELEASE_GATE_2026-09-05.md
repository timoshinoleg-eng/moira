# Moira — release gate evidence — 2026-09-05

Контекст: серия qw-2/qw-3 (2026-09-03) изменила LLM-промпты (`PROMPT_VERSION`
→ `v7-minor-content`, +контент миноров, блок паттернов) и была влита в main
без прогона immutable eval — нарушение правила handoff. Этот документ
фиксирует попытку закрыть гейт, фактические результаты и точный путь
завершения. **Вердикт по качеству v7: INCONCLUSIVE — прогон блокирован
внешними ресурсами, не кодом.**

## Инфраструктура eval (проверено)

| Артефакт | Статус |
|---|---|
| Fixture `tests/fixtures/quality_eval_24.json` | SHA-256 `0a7af8fc…` — совпадает с `docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json` |
| Immutable-базлайн | не изменялся с 2026-08-17 (git-история, единственный коммит `386e5de`) |
| Раннер `scripts/run_oracle_v6_eval.py` | изменён в qw-серии только механически (распаковка `(result, _generation_id)` после qw-0 provenance); SHA-256 в базлайне более не совпадает — это ожидаемо и задокументировано здесь |
| Завершённый 24-кейсовый v6-артефакт | НЕ существует (см. `docs/IMMUTABLE_QUALITY_RUN_REPORT_2026-08-17.md`: BLOCKED_PROVIDER_RELIABILITY, TASK 4 OPEN). Завершён только 6-кейсовый v6 (`docs/QUALITY_EVAL_V6_FULL_RESULTS.json`: 5/6 structured, 0 hard fails) |

Прямое сравнение «v6 vs v7» на одинаковой модели невозможно: нет завершённого
v6-прогона 24 кейсов. Критерий гейта принят: завершённый (`terminal_status:
COMPLETE`) 24-кейсовый прогон текущей прод-конфигурации с `hard_fail_cases:
[]` и контрактными проверками без провалов.

## Прогон 1 — `v7-minor-content-gate-2026-09-05`

Конфигурация: .env как есть → `stealth/ox-alpha`. Результат: **модель
демонтирована провайдером** — OpenRouter отвечает 404 «Thank you for
participating in the Stealth Ox Alpha testing period… Use it now:
`z-ai/glm-5.3-flash`».

| Метрика | Значение |
|---|---|
| terminal_status | COMPLETE |
| Режимы | 24× deterministic_fallback, 0× llm_structured, 0× failed_to_complete |
| hard_fail_cases | 0 |
| product_language_matches | 24/24 |
| share_safe_no_question_echo | 24/24 |
| no_gibberish_markers | 24/24 |
| no_forbidden_safety_claim | 24/24 |
| fallback_draw_contract | 12/24 (все 12 провалов — RU; см. «Баг чекера») |

Ценность прогона: это фактический chaos-тест «провайдер умер». Деградация
отработала штатно: 24/24 кейсов получили валидный детерминированный fallback,
ни одного `failed_to_complete`, ни одного safety-нарушения, язык и приватность
share-строки сохранены на всех кейсах.

## Прогон 2 — `v7-glm53-gate-2026-09-05`

Конфигурация: override модели на `z-ai/glm-5.3-flash` (наследник ox-alpha).
Результат: **403 «Key limit exceeded (total limit)»** на каждом вызове.

Прямая проверка ключа через `GET /api/v1/key`: limit **$0.05** (total, без
reset), usage **$0.0521**, `limit_remaining: 0`. Ключ исчерпан до начала
прогонов; оба прогона не списали ни цента (403/404 не тарифицируются).

## Баг чекера (не регрессия v7)

`scripts/run_oracle_v6_eval.py:153` (`_fallback_draw_contract`) использует
захардкоженные английские токены ориентации `"reversed"/"upright"` и для
всех RU-фолбэков возвращает False: в русском тексте эти токены не встречаются.
Подтверждено прямым вызовом чекера на идентичном payload: RU → False,
EN → True, при этом label и meaning в RU-тексте присутствуют. Это прежний
дефект харнесса (в v6-артефакте fallback_counterparts отсутствуют — старая
схема), он не связан с изменением контента v7. Требует отдельного фикса
раннера до следующего гейта (учитывать `lang` при выборе токена ориентации).

## Операционные находки для владельца (P0-уровня, вне кода)

1. **Модель прод-конфига мертва.** `stealth/ox-alpha` в локальном `.env`
   демонтирована OpenRouter. Пока не заменена, каждый запрос чтения уходит в
   детерминированный fallback. Преемник: `z-ai/glm-5.3-flash` (сообщение
   провайдера). Дефолт compose/`.env.example` (`deepseek/deepseek-v4-flash`)
   не затронут — контейнерные деплои используют его.
2. **Ключ OpenRouter исчерпан.** Total-лимит $0.05 выбран полностью,
   `limit_remaining: 0`. Даже после смены модели генерация не восстановится,
   пока лимит не поднят / ключ не пополнен.
3. До исправления 1–2 любое staging-валидация флагов (этап 5) невозможна.

## Как завершить гейт (после пополнения ключа)

1. Обновить модель: `LLM_MODEL=z-ai/glm-5.3-flash` (или принятый прод-выбор) в `.env`.
2. Если модель из .env нужно переопределить на один прогон: `bot/config.py`
   исполняет `load_dotenv(override=True)` на импорте, shell-env проигрывает.
   Рабочий способ — небольшой wrapper, задающий `os.environ["LLM_MODEL"]`
   ПОСЛЕ `import bot.config` и запускающий раннер через `runpy`; либо
   временная правка `.env` на время прогона.
3. `PYTHONPATH=. EVAL_RUN_ID=<новый-id> EVAL_LIMIT=24 .venv/Scripts/python.exe scripts/run_oracle_v6_eval.py`
   (Python не добавляет cwd в sys.path при запуске файла из `scripts/` — без
   `PYTHONPATH` раннер падает `ModuleNotFoundError: bot`).
4. Критерии PASS: `terminal_status: COMPLETE`, `hard_fail_cases: []`,
   `llm_structured` ≥ 20/24, контрактные проверки без провалов (учитывая баг
   чекера — провалы только по `fallback_draw_contract` на RU-фолбэках).
   Деградация против 6-кейсового v6-референса (5/6 structured, 0 hard fails)
   недопустима.
5. Артефакты этой попытки сохранены: `docs/governing_runs/v7-minor-content-gate-2026-09-05/`
   (приватный owner-review файл игнорируется `.gitignore`, в git не входит).

## Что подтверждено в этой сессии помимо eval

- Фиксы P0×2 (lock-каталог, migrate-сервис) и P1 (FSM заметок) — см. PR из
  ветки `fix/compose-p0-note-fsm`; верифицированы на живом PG 16 и контейнере
  (сборка, 10 миграций, lock, polling-цикл).
- 206 тестов passed; ruff по изменённым файлам без новых находок.
