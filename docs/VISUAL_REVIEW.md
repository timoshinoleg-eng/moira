# Визуальный обзор Moira (VISUAL_REVIEW)

Дата проверки: 2026-08-07. Среда: Linux-песочница, Python 3.11.15, Pillow 12.3.0.
Все изображения сгенерированы реальными функциями `bot/visual/render.py`
(`make_spread_image`, `make_share_image`, `make_single_image`) из рабочей копии
`/home/user/moira` и проверены повторным открытием через Pillow (размер, режим, вес).

## 1. Галерея — 16 изображений

| # | Файл | Размер, px | Mode | КБ | Сценарий | Результат |
|---|------|-----------|------|----|----------|-----------|
| 1 | `altar_en.png` | 1080×1350 | RGB | 756 | Алтарь EN (upright) | ✅ |
| 2 | `altar_ru.png` | 1080×1350 | RGB | 766 | Алтарь RU (реверс) | ✅ |
| 3 | `long_en_names.png` | 1080×1500 | RGB | 1137 | Long EN names (Knight of Pentacles, The High Priestess, Three of Pentacles) | ✅ |
| 4 | `long_ru_names.png` | 1080×1500 | RGB | 1037 | Длинные RU-названия (Восьмёрка Пентаклей, Четвёрка Пентаклей, Шестёрка Пентаклей) | ✅ |
| 5 | `missing_asset.png` | 1080×1500 | RGB | 808 | Без ассета карты (placeholder) | ✅ |
| 6 | `no_font_fallback.png` | 1080×1500 | RGB | 1142 | Без основного шрифта (load_default, graceful) | ✅ |
| 7 | `quiz_result_en.png` | 1080×1350 | RGB | 735 | «Мой Аркан» EN (аркан 12, HTML-подпись) | ✅ |
| 8 | `quiz_result_ru.png` | 1080×1350 | RGB | 722 | «Мой Аркан» RU (аркан 12, HTML-подпись) | ✅ |
| 9 | `share_en.png` | 1080×1080 | RGB | 890 | Share-карточка EN | ✅ |
| 10 | `share_ru.png` | 1080×1080 | RGB | 903 | Share-карточка RU | ✅ |
| 11 | `spread_choice_en_upright.png` | 1080×1500 | RGB | 1159 | «Выбор» EN, все upright | ✅ |
| 12 | `spread_choice_ru_mixed.png` | 1080×1500 | RGB | 1128 | «Выбор» RU, mixed | ✅ |
| 13 | `spread_love_en_reversed.png` | 1080×1500 | RGB | 1154 | «Любовь» EN, все reversed | ✅ |
| 14 | `spread_love_ru_mixed.png` | 1080×1500 | RGB | 1226 | «Любовь» RU, mixed | ✅ |
| 15 | `spread_situation_en_mixed.png` | 1080×1500 | RGB | 1229 | «Ситуация» EN, mixed (1 реверс) | ✅ |
| 16 | `spread_situation_ru_upright.png` | 1080×1500 | RGB | 1116 | «Ситуация» RU, все upright | ✅ |

Все 16 файлов открываются, размеры совпадают с ожидаемыми canvas-размерами,
mode — RGB, вес > 10 КБ. Плюс в каталоге сохранены 4 исходных PNG из архива
(`share_ru.png` — перезаписан новой версией, `single_card.png`, `single_rev.png`,
`spread_ru.png`) и 4 smoke-файла (`*_smoke.png`).

## 2. Шрифт

| Параметр | Значение |
|----------|----------|
| Семейство | PT Serif (Regular + Bold) |
| Лицензия | SIL Open Font License 1.1, Copyright (c) 2010 ParaType Ltd., Reserved Font Names «PT Sans», «PT Serif», «ParaType» |
| Файлы | `assets/fonts/PT_Serif-Web-Regular.ttf` (359 048 б), `assets/fonts/PT_Serif-Web-Bold.ttf` (339 996 б), лицензия `assets/fonts/OFL.txt` |
| Источник | github.com/google/fonts, каталог `ofl/ptserif` (проверено 2026-08-07: HEAD 200, размеры совпали) |
| Покрытие | Core Cyrillic (А-я + Ёё) — ✅, Basic Latin — ✅, цифры/пунктуация — ✅. Отсутствуют исторические кириллические знаки (U+0400, U+040D, Ѣ/ѣ и др.) и декоративные символы (✦ U+2726, ⟲ U+27F2, ★ U+2605, эмодзи) — для контента бота не используются |

Порядок разрешения в `render._font()`: project-local `assets/fonts` (PT Serif) →
системные fallback (C:/Windows/Fonts, DejaVu) → `ImageFont.load_default()` только
как аварийный (try/except). `ImageFont.load_default()` основным шрифтом НЕ является.
Из-за отсутствия в PT Serif декоративных глифов добавлен санитайзер
`_sanitize_text()` (HTML-теги + неподдерживаемые диапазоны Unicode), а маркер
перевёрнутой карты в share-карточках — локализованный текст «(перевёрнутая)/(reversed)»
вместо символа ⟲.

## 3. Design tokens

Модуль `bot/visual/tokens.py` — единый источник всех визуальных констант:

- **Цвета**: фон-градиент (BG_TOP/BG_BOTTOM), тексты 5 уровней (заголовок, основной,
  вторичный, позиции, футер, реверс-подпись), свечение карт GLOW_COLOR, placeholder-панель.
- **Шрифты**: имена файлов Regular/Bold + fallback-имена.
- **Canvas**: CANVAS_SPREAD 1080×1500, CANVAS_SHARE 1080×1080, CANVAS_SINGLE 1080×1350.
  Обоснование: пропорции карт 300×520 ≈ 0.577 (стандарт 2:3.5); 1080 px — штатный размер
  Telegram-фото без дополнительного сжатия; вертикальные форматы для чтения на телефоне.
- **Типографика**: 10 кеглей (21–48) по ролям (заголовок/позиция/имя/подпись/футер на каждом canvas).
- **Layout**: размеры карт, отступы, координаты Y, лимиты строк и ширины обёртки текста.
- **Декор**: число/радиус/альфа звёзд, параметры свечения, радиус placeholder.
- **Вывод**: качество JPEG.

Магических чисел в функциях Pillow больше нет (проверено: 15 цветовых литералов и
10 кеглей до рефакторинга, 0 после — всё импортируется из tokens.py).

## 4. Исправления, внесённые в render.py (в рамках Блока 1)

1. EN-расклады больше не подписывают перевёрнутые карты русским словом
   («перевёрнутая» → `REVERSED_NOTE[lang]`); параметр `lang` прокинут из обработчиков
   (`reading.py`, `features.py`).
2. HTML-теги `<b>/<i>` из `format_arcana_result()` (quiz-результат) больше не рисуются
   буквально — `_sanitize_text()` перед отрисовкой.
3. Отсутствующий ассет карты → аккуратная placeholder-панель (скруглённая, с рамкой)
   вместо пустой области (`missing_asset.png`).
4. Неподдерживаемые глифы (эмодзи, ✦, ⟲, ★) удаляются санитайзером — нет «квадратиков» tofu.

## 5. Ограничения / ручная проверка

- Эмодзи в заголовках (например 🌙 в «Твой алтарь») не выводятся (нет глифа в PT Serif) —
  заголовок отображается текстом без эмодзи. Если нужно эмодзи на картинке — нужен
  эмодзи-шрифт (Noto Color Emoji) и отдельная отрисовка.
- Реальный вид на телефоне (Telegram-сжатие JPEG, тёмная тема) — ручная проверка.
- Отрисовка на Windows-машине пользователя пойдёт через тот же project-local шрифт. 
Continuation 2026-08-16: preserved the existing 78-card source artwork and provenance, added a restrained gold frame to card placements, and retained the existing font-safe glyph sanitization. Real-device Telegram visual review remains required after Telegram API availability is restored.
Continuation 2026-08-16 visual polish: source deck remains 78/78 unchanged. Renderer now adds a dark altar matte, modest inset, gold upright frame and rose reversed frame around source artwork. Spread card group moved downward (y=330) and footer lifted for a more balanced 1080x1500 composition. Reviewed RU spread, RU share and reversed single-card representative outputs; typography, Cyrillic labels, orientation and share-safe content are readable at renderer level. Real Telegram compression/device checks remain BLOCKED.
