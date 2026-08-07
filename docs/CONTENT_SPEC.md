# Спецификация контента Moira (CONTENT_SPEC)

## 1. Экраны и тексты

### 1.1 Onboarding (/start)

| Поле | RU | EN | Переменные | Макс. длина |
| --- | --- | --- | --- | --- |
| greeting | ✨ Я {name} — твой ИИ-оракул... | ✨ I'm {name}, your AI oracle... | {name}, {free} | 400 |

### 1.2 Главное меню

| Ключ | RU | EN | Кнопка |
| --- | --- | --- | --- |
| btn_situation | 🃏 Ситуация | 🃏 Situation | spread:situation |
| btn_love | ❤️ Любовь | ❤️ Love | spread:love |
| btn_choice | ⚖️ Выбор | ⚖️ Choice | spread:choice |
| btn_altar | 🌙 Мой алтарь | 🌙 My altar | altar |
| btn_quiz | 🎭 Мой Аркан | 🎭 My Arcana | quiz |
| btn_history | 📖 Мои расклады | 📖 My readings | history |

### 1.3 Выбор расклада

| Расклад | RU описание | EN описание |
| --- | --- | --- |
| situation | Три карты: суть происходящего, скрытый фактор и следующий шаг | Three cards: what is really going on, a hidden factor, and the next step |
| love | Три карты: твоё состояние, динамика связи и полезный фокус | Three cards: your state, the relationship dynamic, and a helpful focus |
| choice | Три карты: потенциал пути А, потенциал пути Б и критерий решения | Three cards: potential of path A, potential of path B, and a decision criterion |

### 1.4 Ввод вопроса

| Поле | RU | EN |
| --- | --- | --- |
| ask_question | Загадай вопрос и отправь его сообщением. Или отправь «-», чтобы расклад был общим. | Type your question and send it. Or send '-' for a general reading. |
| shuffling | Тасую карты… 🔮 | Shuffling the deck… 🔮 |

### 1.5 Результат расклада

| Поле | RU | EN | Примечание |
| --- | --- | --- | --- |
| spread_interpretation_header | Трактовка (нажми, чтобы открыть): | Interpretation (tap to reveal): | Заголовок секции |
| spread_synthesis_header | Общий вывод: | Synthesis: | Заголовок синтеза |
| reading_actions | Расклад сохранён в дневник 📖 | Reading saved to your diary 📖 | После сохранения |

### 1.6 Fallback

| Поле | RU | EN |
| --- | --- | --- |
| template_note | (Базовый режим трактовки...) | (Basic interpretation mode...) | Показывается без API ключа |

### 1.7 Алтарь и Карта дня

| Поле | RU | EN | Переменные |
| --- | --- | --- | --- |
| altar_header | 🌙 Твой алтарь — {date} | 🌙 Your altar — {date} | {date} |
| altar_card | Карта дня: {card}{rev} | Card of the day: {card}{rev} | {card}, {rev} |
| altar_phase | 🌒 {phase} — {meaning} | 🌒 {phase} — {meaning} | {phase}, {meaning} |
| altar_moonin | ♑ Луна в знаке {sign}: {text} | ♑ Moon in {sign}: {text} | {sign}, {text} |

### 1.8 Тест «Мой Аркан»

| Поле | RU | EN |
| --- | --- | --- |
| quiz_intro | 🎭 Тест «Мой Аркан»: 6 вопросов — и карты покажут твой архетип. Готов(а)? | 🎭 „My Arcana“ quiz: 6 questions — and the cards reveal your archetype. Ready? |
| quiz_progress | Вопрос {n}/6 | Question {n}/6 |
| quiz_result_title | Твой Аркан — {name}! | Your Arcana is {name}! |

### 1.9 Недельное зеркало

| Поле | RU | EN |
| --- | --- | --- |
| mirror_title | 🪞 Зеркало недели | 🪞 Mirror of the week |

### 1.10 Голос

| Поле | RU | EN |
| --- | --- | --- |
| voice_title | Голос оракула | Oracle voice |
| voice_unavailable | 🎧 Голосовые сообщения недоступны... | 🎧 Voice messages are not available... |

### 1.11 Ошибки и safety

| Поле | RU | EN |
| --- | --- | --- |
| reading_failed | ⚠️ Не удалось подготовить расклад. Попробуй ещё раз — кредит не списан. | ⚠️ Could not prepare the reading. Please try again — no credit was charged. |
| safety_refusal | ⚠️ Я не могу давать медицинские, юридические или финансовые рекомендации... | ⚠️ I can't give medical, legal or financial advice... |

## 2. Голос Moira (Tone of Voice)

### Принципы:
- Женский род, спокойный и уверенный тон
- Лёгкая мистическая атмосфера без клише
- Никаких «я чувствую твою энергию», «такова твоя судьба»
- Не утверждать, что видит будущее
- Не повторять имя пользователя в каждом абзаце
- Не начинать все ответы одинаково

### Баланс тона:
- 20% атмосфера
- 60% ясная интерпретация
- 20% практическая рефлексия

## 3. Длина текстов

| Элемент | Длина |
| --- | --- |
| Headline | до 90 символов |
| Opening | 120–250 символов |
| Одна карта | 300–550 символов |
| Synthesis | 500–900 символов |
| Practical focus | 180–350 символов |
| Reflection question | до 220 символов |
| Voice summary | 500–800 символов |
| Share summary | 180–300 символов |

## 4. Ограничения

- Только RU и EN локали
- Никаких других языков
- Неизвестная локаль → fallback на RU
- Технический ключ не показывается пользователю
