# Ночной блок ZCode — 2026-08-17 (инженерия релиза)

Часть тройной ночной смены (ZCode / ChatGPT / Manus). Мой контур: seal релиза,
провайдер-гейт, деплой-артефакты, fresh-install. Чужие файлы не трогал:
ChatGPT работает по новым standalone-файлам, Манус — в своей копии.

## 1. Seal RC — ГОТОВО (локально), push заблокирован

- Рабочее дерево запечатано коммитом `81e6a8a` (ветка `feat/moira-production-readiness`),
  тег **`v6-rc2`**: provider-routing/backup-model/JSON-mode, clipping полей схемы,
  runtime-lock v2, retry-loop polling, визуальный matte/frame, oracle v6 contract,
  eval-скрипты и smoke-выводы, 119 тестов.
- В коммит НЕ попали: `.env`, БД, `Moira.png`, `Манус Мойра/`, `.moira-video-analysis/`,
  owner-private JSON (`docs/*PRIVATE*.json`) — добавлены в `.gitignore`.
- **Push не выполнен**: токен в remote URL истёк (`ghp_…` в `.git/config`),
  `gh auth` для `timoshinoleg-eng` невалиден. Действие владельца утром:
  `gh auth login -h github.com`, затем
  `git push -u origin feat/moira-production-readiness && git push origin v6-rc2`.
  Заодно убрать токен из remote-URL (`git remote set-url origin https://github.com/timoshinoleg-eng/moira.git`).

## 2. Провайдер-гейт — частично; бэкап-модель сломана

Config-smoke (`scripts/openrouter_config_smoke.py`, ключ не раскрывается):

| Модель | content | finish_reason | Вердикт |
|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` (primary) | непустой | stop | рабочий |
| `liquid/lfm-2.5-2.6b:free` (backup) | **пустой** | **length** | **сломан: весь budget уходит в reasoning, content не возвращается** |

Вывод: backup-модель бесполезна для structured-чтений — любой fallback-атtempt
обречён. Рекомендация: заменить на `openai/gpt-oss-20b:free` (был рабочим
primary ранее) или на платный `deepseek/deepseek-chat-*` (стоимость 24-кейс
прогона < $0.05). Решение за владельцем (платный путь требует кредитов).

Полный 24-кейс прогон: см. секцию 5 (статус ниже).

## 3. deploy/ — ГОТОВО

- `deploy/moira.service` — systemd unit (из PRODUCTION_RUNBOOK, теперь в репо);
- `deploy/moira-backup.sh` — online backup + retention;
- `deploy/moira-restore-drill.sh` — восстановление в изолированную папку + integrity;
- `deploy/win_backup.py` — переходный nightly-бэкап для локальной Windows-машины;
- `deploy/README.md` — bootstrap VPS одной страницей + cron + чек-лист + Windows-вариант.

Проверено на живой машине: `win_backup.py` снял консистентную копию работающего
бота, `integrity_check=ok`, данные на месте (users=2, readings=7, llm_usage=109).

## 4. Fresh-install на теге v6-rc2 — PASS

`C:\moira_fresh\app` (ASCII-путь): clone по тегу → venv → `pip install -r requirements-dev.txt`
→ `alembic upgrade head` (0002→0005) → `alembic check` clean → **pytest 119 passed**
→ 78 card images на месте. Воспроизводимость релиза подтверждена на запечатанном SHA.

## 5. Quality-гейт 24 кейса — ДВА ПОЛНЫХ ПРОГОНА,(provider-критерий) PASS

- RUN1: 22/24 structured (91.7%), 2 fallback, **0 hard-fail**.
- RUN2: 23/24 structured (95.8%), 1 fallback, **0 hard-fail**.
- Незначительные промахи чеков: reflection_question 1/22, mystical_imagery 1/22.
- Вчерашний блокер «прогоны обрываются на malformed/truncated выводе» снят:
  оба прогона дошли до конца, деградация до безопасного fallback отработала
  штатно. Полный отчёт: `docs/QUALITY_GATE_RUN_2026-08-17.md`.
- Для полного закрытия TASK 4 остаётся утренний шаг владельца: слепое
  рубрик-ревью LLM vs fallback (приватные JSON подготовлены).

## 6. Не делал (чужие контуры / требует владельца)

- Не менял настройки живого бота (процесс крутится, .env не трогал).
- Не заказывал платные модели (нужны кредиты владельца).
- Не пушил под чужим аккаунтом `glebforewer-ui`.

## Утренние действия владельца (по убыванию приоритета)

1. `gh auth login` → push ветки и тега (бэкап кода off-site).
2. Решение по LLM: заменить backup-модель (минимум) или перевести primary на
   платный надёжный маршрут (максимум) — затем финальный 24-кейс прогон.
3. Живой E2E-чеклист по `docs/PRODUCTION_RUNBOOK.md` с тестовым аккаунтом
   (15–20 минут вручную; автоматизировать нельзя без аккаунта).
4. Принять/отклонить патч ChatGPT (watchdog/telemetry) после ревью Мануса.
