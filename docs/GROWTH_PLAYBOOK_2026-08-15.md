# Moira Growth Playbook — organic growth, retention and monetization

**Версия:** 15 августа 2026  
**Цель:** построить повторяемый органический цикл роста вокруг частного Tarot Journal, а не вокруг одноразовых предсказаний.

## 1. Product Thesis

Moira не должна пытаться стать ещё одним «ботом, который отвечает на любой вопрос». Её сильное и этичное ядро — **короткий личный расклад, который помогает сформулировать вопрос, увидеть паттерн и вернуться к нему позже**. Это сочетает удобство Telegram с тем, что напрямую обещают и развивают сильные категории-конкуренты: history, follow-up, reminders и value of journal.[1] [2]

> Формула продукта: **Вопрос → три карты → ясный следующий шаг → приватный Journal → короткое продолжение → добровольный share.**

## 2. What Was Implemented

| Change | Purpose | User value | Metric |
|---|---|---|---|
| Native invite flow on existing `🎁 Позвать друга` button | Закрыть ранее отсутствовавший callback и сделать referral loop доступной | Личная referral-ссылка и нативный Telegram share sheet | `invite_opened`, referred signups, activation per invite |
| Stable A/B attribution (`a` / `b`) in invite deeplink | Сравнить два текста без смешивания cohorts | Более понятное измерение share-to-reading conversion | signup per share, first reading per signup |
| Privacy-safe share CTA | Не просить публиковать личный вопрос в комментариях | Пользователь ведёт друга в private bot dialogue | Click-to-start rate |
| Value-led paywall text | Продавать продолжение полезной практики, а не дефицит | Честное объяснение покупки | paywall → purchase conversion |
| Corrected 30-day label | Не называть разовый доступ подпиской | Доверие и меньше refund/confusion risk | payment support complaints/refunds |

## 3. North Star and Guardrails

Основная метрика на раннем этапе — не выручка, а **количество пользователей, которые завершили первый расклад и вернулись к нему в течение семи дней**. Первые платные механики должны усиливать уже понятную ценность: дополнительные глубокие чтения, сохранённый контекст и продолжение своей записи, а не закрывать базовую безопасность или историю.

| Stage | North-star metric | Secondary signals | Do not optimize yet |
|---|---|---|---|
| 0–50 testers | First reading completion | share click, feedback, follow-up click | ARPU |
| 50–250 users | 7-day revisit / second reading | D1 return, reading quality score | Complex segmentation |
| 250–1,000 users | Qualified referral activation | invited start → reading completion | Large paid creator spend |
| 1,000+ users | Paid conversion after demonstrated value | refund rate, unlimited-pass usage | New platforms before retention is stable |

## 4. Viral Loops to Build and Measure

### Loop A — private invitation

A completed reading ends with one optional action: **«Это откликнулось? Отправь другу личную ссылку на его первый вопрос»**. The new invite flow implements the technical side: a unique deeplink, native Telegram share and A/B attribution. Reward the referrer only after the invited user pays, as current payment logic already does; this protects against low-quality invite spam.

**Experiment A/B copy:**

| Variant | RU share copy | Hypothesis |
|---|---|---|
| A | «Попробуй личный расклад с Мойрой — бережный ИИ-таро в Telegram. Начни с вопроса, который действительно важен.» | Gentle self-reflection attracts high-quality starts. |
| B | «Когда вопрос не отпускает, три карты помогают увидеть ситуацию яснее. Личный расклад в Telegram — по этой ссылке.» | Concrete tension and outcome increase click-through. |

Stop neither variant before **30 attributed starts and 15 completed first readings per variant**. Comments, views and raw shares are vanity indicators unless the journey reaches a completed reading.

### Loop B — shareable card, private context

Every finished reading may produce a beautiful card/spread image, but the public visual must contain **only card names, a neutral reflective phrase and the bot handle**. Never include the original question or a sensitive interpretation in public share text. A share is a story prompt, not disclosure.

Recommended short overlays:

| Asset | RU overlay | EN overlay |
|---|---|---|
| Daily card | «Карта дня: что стоит заметить?» | “Card of the day: what is worth noticing?” |
| Relationship reading | «Не “что он чувствует?”, а “что мне важно понять?”» | “Not ‘what do they feel?’ — ‘what matters for me to understand?’” |
| Choice spread | «Три точки ясности перед решением» | “Three points of clarity before a choice” |
| Journal recap | «Вернись к тому, что уже стало яснее» | “Return to what has already become clearer” |

### Loop C — question craft content

The second Moira video already demonstrates an unusually defensible brand habit: moving from a question about someone else’s thoughts to a question about the user’s own understanding. Turn it into a recurring social and in-bot format: **«Вопрос недели: перепиши его с Мойрой»**. It works as education, as a safe product differentiator and as an acquisition hook.

## 5. Content System: Ready-to-produce 14-Day Plan

No paid influencer purchase is required. Each short vertical piece should have a one-line subtitle hook, a visible Telegram CTA and one product proof screen in the last two seconds. The existing HeyGen avatar provides a consistent character; do not create a new persona.

| Day | Format | First two seconds | Core line | CTA |
|---:|---|---|---|---|
| 1 | Video | «Карты — не приговор.» | «Они помогают заметить то, что уже важно.» | «Личный расклад — в Telegram.» |
| 2 | Carousel | «Не спрашивай: “Он меня любит?”» | «Спроси: “Что мне важно понять об этих отношениях?”» | «Перепиши вопрос с Мойрой.» |
| 3 | Daily card | Close-up of one card | «Не предсказание. Один вопрос к себе.» | «Открой карту дня.» |
| 4 | Video | «Застрял в выборе?» | «Три карты не решат за тебя, но покажут, что ты не учёл.» | «Разбери решение в Telegram.» |
| 5 | Quote card | «Я вернулась к раскладу через неделю…» | «…и увидела другой смысл.» | «Сохраняй расклады в Journal.» |
| 6 | Video | «Почему ответы Таро иногда раздражают?» | «Потому что вопрос был слишком узким.» | «Дай Мойре переформулировать.» |
| 7 | Share card | Three card names, no question | «Три точки ясности» | «Спроси свой вопрос.» |
| 8 | Video | «Если страшно тянуть карту…» | «Начни не с будущего, а с того, что можешь поддержать сегодня.» | «Безопасный расклад — в Telegram.» |
| 9 | Carousel | «3 вопроса перед важным разговором» | «Что я хочу сказать? Что боюсь услышать? Что могу сделать бережно?» | «Сохрани и открой расклад.» |
| 10 | Daily card | Candle + one card | «Какая тема просит внимания?» | «Карта дня в боте.» |
| 11 | Video | «Таро не читает чужие мысли.» | «Но может помочь увидеть твой следующий честный шаг.» | «Спроси Мойру.» |
| 12 | Journal recap | Simple timeline graphic | «Расклад — это не одно сообщение. Это заметка о пути.» | «Вернись к своим картам.» |
| 13 | Video | «Что делать после расклада?» | «Выбери один маленький шаг, а не десять обещаний.» | «Сохрани следующий шаг.» |
| 14 | Invite | Friend-to-friend visual | «Есть вопрос, который не хочется обсуждать публично?» | «Отправь другу private link.» |

## 6. Visual System for Social and Bot Shares

Retain the existing premium dark-study aesthetic: deep charcoal/near-black, warm candlelight, soft muted gold and ivory text. The social system needs more evidence of the product than the current talking-head videos.

| Element | Rule | Rationale |
|---|---|---|
| Presenter | Use Moira only as a short 5–9 second hook | Reduces avatar fatigue and keeps character recognition. |
| Captions | Always on; large ivory text, one idea per frame | Viewers frequently experience short video muted. |
| Cards | Use one card close-up or three-card visual as cutaway | Adds movement and retains Tarot specificity. |
| Product proof | 1–2 seconds of real Telegram UI/result at end | Makes product route obvious. |
| CTA | `Спроси Мойру в Telegram` + bot handle/deeplink | Converts attention into one clear action. |
| Privacy | Never tell viewers to write a personal question in public comments | Matches Moira’s reflective and private positioning. |

## 7. Copy Improvements to Apply Later

| Surface | Current direction | Recommended replacement principle |
|---|---|---|
| Onboarding | Explain product in one sentence before options | «Три карты, чтобы яснее увидеть свой вопрос — не предсказание вместо твоего решения.» |
| Question input | Lower pressure, improve question quality | «Что сейчас важнее всего прояснить? Можно написать коротко и своими словами.» |
| Result ending | One grounded next step | «Выбери один маленький шаг, который поддержит тебя в ближайшие сутки.» |
| Follow-up | Constraint instead of endless chat | «Углубить карту», «Что я не замечаю?», «Какой следующий шаг?» |
| Paywall | Value after proof, not false urgency | «Продолжи разбирать важный вопрос и возвращайся к сохранённым картам.» |
| Referral | Private benefit, clear terms | «Друг начнёт в личном диалоге; награда начисляется после его первой покупки.» |

## 8. Monetization Roadmap

### Now: prove value, do not maximize pressure

Keep the existing one-reading and time-pass purchases. The revised 30-day label should remain a **30-day unlimited pass** unless the payment implementation becomes truly recurring. Do not promise “subscription” when the current entitlement is a time-bounded paid access.

### After 50 retained users: introduce depth, not a hard wall

Create a voluntary **Journal Deep Dive** pack: a reading, three constrained follow-ups and one weekly mirror. It may be sold as a package only after users understand the basic free flow. The paid unit is continuity and reflection, not a claim of better fortune-telling.

### After 250 users: test two simple offers

| Offer | User receives | Why it can work |
|---|---|---|
| 7-day Reflection Pass | Unlimited readings plus daily/weekly prompts | Fits an intensive decision or relationship period. |
| Journal Deep Dive | One reading + three recorded follow-ups + mirror recap | Makes a clear, finite high-intent purchase. |

Do not introduce ads inside readings. Both Labyrinthos’ public position and Moira’s product trust depend on a contemplative, interruption-free experience.[2]

## 9. Measurement Plan

Use the local events table and PostHog only for allowlisted, non-sensitive properties. Never send question text, reading text, names, usernames or media URLs to analytics.

| Funnel step | Event | Required properties |
|---|---|---|
| Content entry | `bot_started_from_video` | `campaign`, `creative`, `variant` |
| Invite intent | `invite_opened` | `caption_variant` |
| Referral signup | existing `referral_signup` | `caption_variant` |
| Activation | existing `referral_first_reading` | `caption_variant`, `spread`, `mode` |
| First value | `reading_completed` | `spread`, `mode`, `source` |
| Depth | `followup_opened` | `followup_kind`, `mode` |
| Retention | `history_reopened` | `days_since_reading` bucket |
| Purchase | existing payment events | product only, never card/question text |

## 10. Available Capabilities and Integrations

| Capability | Current availability | Best use | Activation boundary |
|---|---|---|---|
| HeyGen | Enabled | Produce short Moira avatar variants from the scripts above | Generate drafts only; obtain approval before publishing. |
| GitHub | Enabled | Version and review source changes | Keep existing local uncommitted changes separate. |
| Google Workspace | Enabled | Store a testing sheet or editorial rubric | Use only if the owner requests shared collaboration. |
| Linear | Enabled | Track the backlog and experiments | Create issues only if the owner asks to use the project board. |
| PostHog | Available but disabled | Funnel dashboard and A/B flags | Enable only when analytics credentials and privacy scope are confirmed. |
| Instagram / Buffer / Metricool / Ayrshare / Blotato | Available but disabled | Schedule approved organic posts and compare creative variants | Do not enable or publish without owner confirmation. |
| Bitly | Available but disabled | Branded short URLs/QR attribution | Enable only after a public landing/deeplink strategy is chosen. |
| Brand24 | Available but disabled | Monitor brand mentions and creator feedback | Enable only when social handles and monitoring scope are agreed. |

## 11. 30-Day Operating Cadence

| Week | Outcome | Work |
|---:|---|---|
| 1 | Validate technical loop | Deploy invite fix; test deep links on a real bot; create 4 captioned video variants; define dashboard events. |
| 2 | Validate first value | Invite 20 testers; collect completion/feedback/follow-up data; run 20-case content-quality review. |
| 3 | Validate organic loop | Publish/seed 6 approved pieces; compare CTA A/B; identify which content produces completed readings, not only views. |
| 4 | Validate payment fit | Offer one value-led pass only to users who completed 2+ readings; inspect conversion, refunds and user feedback. |

## References

[1]: https://apps.apple.com/us/app/ai-tarot-reading-chat/id6449005723 "AI Tarot: Reading Chat — Apple App Store"
[2]: https://apps.apple.com/us/app/labyrinthos-tarot-reading/id1155180220 "Labyrinthos Tarot Reading — Apple App Store"
[3]: https://apps.apple.com/jo/app/tarotale-ai-tarot-reading/id6739936019 "Tarotale — AI Tarot Reading — Apple App Store"
[4]: https://sibyls.ai/ "Sibyl AI — official website"
[5]: https://ritualmate.com/ "RitualMate — official website"
