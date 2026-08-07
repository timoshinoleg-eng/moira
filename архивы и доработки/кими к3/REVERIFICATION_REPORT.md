# Отчёт перепроверки Moira

Дата: 2026-08-07. Среда перепроверки: Linux-песочница, Python 3.11.15, рабочая копия `/home/user/moira`
(оригинал архива — `/home/user/moira_extract`, не тронут).

## Результаты тестов

```
$ python -m pytest tests/ -q
77 passed in 4.74s
```
Итого: **77 passed, 0 failed** (было 17 на старте фазы).

## Колода

```
$ python -m pytest tests/test_cards_78.py -q
10 passed in 0.06s
```
78 карт (22 Старших + 56 Младших), полный RU/EN, upright/reversed.
Ассеты: `check_assets()` → (78, 78).

## Fallback

```
$ python -m pytest tests/test_fallback.py -q
7 passed in 0.03s
```

## Мой Аркан

```
$ python tests/test_patch5_i18n_quiz.py
PATCH 5 TESTS PASSED
```
(скриптовый тест, не собирается pytest'ом; статус: PASSED)
Демонстрация `compute_result()` на 5 наборах ответов: [0..0]→12, [1..1]→4, [2..2]→2, [3..3]→19, [0,1,2,3,0,1]→10 (все в диапазоне 0–21).

## Визуал

Сводка из `docs/VISUAL_REVIEW.md` (подробности там):
- 16 изображений в `artifacts/visual_review/` — все проверены Pillow (размер/режим/вес): ✅.
- Шрифт PT Serif (SIL OFL 1.1, ParaType) в `assets/fonts/` — кириллица + латиница; `ImageFont.load_default()` только как аварийный fallback.
- Design tokens: `bot/visual/tokens.py` (цвета, шрифты, canvas 1080×1500/1080×1080/1080×1350, кегли, отступы, декор); в Pillow-функциях магических чисел нет.

## 48 контентных сценариев

```
$ python -m pytest tests/test_content_cases.py -q
49 passed in 0.06s
```
`tests/content_cases.json` — 48 сценариев (8 наборов × 3 расклада × RU/EN), все проходят.

## LLM-схема (Блок 5)

```
$ python -m pytest tests/test_llm_schema.py -q
11 passed in 0.34s
```
Валидаторы длин по ТЗ + voice_summary ≠ synthesis + приватность share_summary.

## Интеграционный smoke

Сводка из `docs/INTEGRATION_SMOKE.md`: **15/15 ✅** (импорты, deck→fallback RU/EN,
make_spread/share/single_image, compute_result ×5, voice_summary отдельное поле,
voice dry-run с моком edge-tts, clean_for_speech).

## Расхождения с предыдущим отчётом

Заявлено ранее как «готово» → фактически в архиве:
- **«Визуал готов»** — в `artifacts/visual_review/` было только 4 PNG (`spread_ru.png`,
  `share_ru.png`, `single_card.png`, `single_rev.png`); `assets/fonts/` отсутствовал;
  `render.py` указывал на `C:/Windows/Fonts` и на Linux рисовал всё через
  `ImageFont.load_default()` (Aileron без кириллицы); в EN-раскладах подпись
  перевёрнутой карты была русской «перевёрнутая»; quiz-изображение выводило
  HTML-теги `<b>/<i>` как текст. Всё это исправлено в этой фазе.
- «17 passed» — подтверждено (baseline 17 passed на чистой копии).
- Остальные блоки (78 карт, fallback, «Мой Аркан», i18n, промпт/схема, патчи 1–5,
  стабилизация) — подтверждены повторным прогоном, расхождений нет.

## Что требует ручной проверки

- поллинг с реальным Telegram-токеном
- реальный TTS-звук (edge-tts)
- отрисовка на телефоне
- восприятие RU/EN пользователями
