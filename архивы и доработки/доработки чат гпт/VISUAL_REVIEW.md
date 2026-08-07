# Visual review Moira

Дата проверки: 2026-08-07.

## Итог

Визуальная система вынесена в единый модуль `bot/visual/tokens.py`. Галерея
`artifacts/visual_review/` содержит ровно 16 обязательных PNG-сценариев. Каждый
файл после генерации открыт Pillow, прошёл `Image.verify()`, имеет ненулевой
размер, режим `RGB` и canvas в диапазоне 640–2160 px. Дополнительно галерея была
просмотрена как contact sheet: явных обрезаний карт, наложений подписей и выхода
текста за canvas не обнаружено.

Для трёхкарточного spread используется `1080×1080`: квадрат лучше сохраняет
читаемость трёх карт в превью Telegram. Share, single card, altar и quiz result
используют портретный `1080×1350`.

## Design tokens

Источник истины: `bot/visual/tokens.py`.

В него вынесены:

- палитра: фон, основной/вторичный/приглушённый текст, accent, gold, frame,
  star/glow и placeholder;
- project-local и OS fallback-шрифты;
- размеры canvas;
- размеры карт, gap, margins, line heights;
- размеры заголовков, подписей, footer и минимальные размеры шрифта;
- параметры glow/stars и placeholder;
- формат/качество production-изображений.

`bot/visual/render.py` использует эти значения вместо локальных визуальных
«магических чисел» для размеров, цветов и шрифтов.

## Шрифт

Основной шрифт при проверке: **Liberation Serif Regular / Bold**.

- Лицензия: **SIL Open Font License 1.1**.
- Лицензионная запись: `assets/fonts/OFL-Liberation.txt`.
- Ожидаемые project-local пути:
  - `assets/fonts/LiberationSerif-Regular.ttf`
  - `assets/fonts/LiberationSerif-Bold.ttf`
- Покрытие, использованное в галерее: кириллица + латиница.
- Порядок fallback: project-local → системные Georgia/Arial/Segoe UI/
  Liberation/DejaVu → `ImageFont.load_default()` только как аварийный вариант.

Примечание к выдаваемому архиву: бинарные файлы шрифтов не включаются в
скачиваемый артефакт; инструкция и лицензия остаются в `assets/fonts/README.md`.
До добавления project-local файлов рендерер продолжает работать через системный
fallback.

## Галерея

| # | Файл | Размер | KB | Сценарий | Результат | Ограничения |
|---:|---|---:|---:|---|---|---|
| 1 | `spread_situation_ru_upright.png` | 1080×1080 | 939.2 | «Ситуация», RU, все upright | ✅ | — |
| 2 | `spread_situation_en_mixed.png` | 1080×1080 | 952.3 | Situation, EN, mixed | ✅ | — |
| 3 | `spread_love_ru_mixed.png` | 1080×1080 | 1011.1 | «Любовь», RU, mixed | ✅ | — |
| 4 | `spread_love_en_reversed.png` | 1080×1080 | 1073.3 | Love, EN, все reversed | ✅ | — |
| 5 | `spread_choice_ru_mixed.png` | 1080×1080 | 933.3 | «Выбор», RU, mixed | ✅ | — |
| 6 | `spread_choice_en_upright.png` | 1080×1080 | 978.2 | Choice, EN, все upright | ✅ | — |
| 7 | `share_ru.png` | 1080×1350 | 841.1 | Share-карточка RU | ✅ | — |
| 8 | `share_en.png` | 1080×1350 | 797.2 | Share-карточка EN | ✅ | — |
| 9 | `altar_ru.png` | 1080×1350 | 806.9 | Алтарь RU | ✅ | — |
| 10 | `altar_en.png` | 1080×1350 | 802.5 | Altar EN | ✅ | — |
| 11 | `quiz_result_ru.png` | 1080×1350 | 617.9 | «Мой Аркан» RU | ✅ | — |
| 12 | `quiz_result_en.png` | 1080×1350 | 617.6 | My Arcana EN | ✅ | — |
| 13 | `long_ru_names.png` | 1080×1080 | 910.6 | длинные русские названия | ✅ | font-fit/wrap до 2 строк |
| 14 | `long_en_names.png` | 1080×1080 | 1008.2 | long English names | ✅ | font-fit/wrap до 2 строк |
| 15 | `no_font_fallback.png` | 1080×1350 | 664.8 | основной/OS шрифт искусственно недоступен | ✅ | намеренно деградированная типографика Pillow default |
| 16 | `missing_asset.png` | 1080×1350 | 173.1 | отсутствует card asset | ✅ | вместо карты — оформленный MOIRA placeholder |

## Воспроизводимость

Команда генерации:

```powershell
./.venv/Scripts/python.exe tests/generate_visual_review.py
```

Фактический вывод проверки в sandbox:

```text
spread_situation_ru_upright.png: (1080, 1080), RGB, 961713 bytes
spread_situation_en_mixed.png: (1080, 1080), RGB, 975129 bytes
spread_love_ru_mixed.png: (1080, 1080), RGB, 1035358 bytes
spread_love_en_reversed.png: (1080, 1080), RGB, 1099010 bytes
spread_choice_ru_mixed.png: (1080, 1080), RGB, 955696 bytes
spread_choice_en_upright.png: (1080, 1080), RGB, 1001639 bytes
share_ru.png: (1080, 1350), RGB, 861274 bytes
share_en.png: (1080, 1350), RGB, 816346 bytes
altar_ru.png: (1080, 1350), RGB, 826286 bytes
altar_en.png: (1080, 1350), RGB, 821775 bytes
quiz_result_ru.png: (1080, 1350), RGB, 632701 bytes
quiz_result_en.png: (1080, 1350), RGB, 632378 bytes
long_ru_names.png: (1080, 1080), RGB, 932436 bytes
long_en_names.png: (1080, 1080), RGB, 1032367 bytes
no_font_fallback.png: (1080, 1350), RGB, 680799 bytes
missing_asset.png: (1080, 1350), RGB, 177263 bytes
```

## Что всё ещё требует ручной проверки

- отображение на реальных экранах Telegram/iOS/Android;
- субъективная читаемость и эстетика RU/EN у пользователей;
- соответствие project-local шрифта реальному production-пакету после его
  добавления на Windows/VPS.
