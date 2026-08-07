"""My Arcana quiz: 6 questions -> Major Arcana archetype."""
from __future__ import annotations

from dataclasses import dataclass, field

# 22 Major Arcana numbers
ALL_MAJOR = list(range(22))

# Scoring weights: each answer gives weight to multiple Arcana
# Format: (text_ru, text_en, weights_dict)
# weights_dict: {arcana_num: weight}

QUIZ_QUESTIONS: list[list[tuple[str, str, dict[int, int]]]] = [
    # Q1: Reaction to uncertainty (primary: 0, 1, 2, 3)
    [
        ("Делаю шаг в неизвестность — доверяю интуицию", "I leap into the unknown — I trust my gut",
         {0: 3, 17: 2, 7: 1}),
        ("Собираю информацию, строю план", "I gather information and make a plan",
         {1: 3, 4: 2, 11: 1}),
        ("Прислушиваюсь к внутреннему голосу и знакам", "I listen to my inner voice and the signs",
         {2: 3, 9: 2, 18: 1}),
        ("Опираюсь на то, что уже проверено и надёжно", "I rely on what is already proven and reliable",
         {3: 3, 6: 2, 5: 1}),
    ],
    # Q2: Decision-making style (primary: 4, 5, 6, 7)
    [
        ("Сердцем — чувствую, что правильно", "With my heart — I feel what is right",
         {6: 3, 3: 2, 14: 1}),
        ("Логикой и анализом фактов", "With logic and analysis of facts",
         {4: 3, 11: 2, 8: 1}),
        ("Интуицией и образами из снов", "With intuition and images from dreams",
         {5: 3, 2: 2, 20: 1}),
        ("Советом тех, кому доверяя", "With advice from those I trust",
         {7: 3, 19: 2, 1: 1}),
    ],
    # Q3: Relationship with control (primary: 8, 9, 10, 11)
    [
        ("Контроль — это безопасность; люблю порядок", "Control is safety; I love order",
         {8: 3, 4: 2, 14: 1}),
        ("Контроль — это клетка; предпочитаю свободу", "Control is a cage; I prefer freedom",
         {9: 3, 0: 2, 15: 1}),
        ("Контроль — это иллюзия; учусь отпускать", "Control is an illusion; I learn to let go",
         {10: 3, 12: 2, 16: 1}),
        ("Контроль — это ответственность; берёшь и делаешь", "Control is responsibility; you take and do",
         {11: 3, 1: 2, 13: 1}),
    ],
    # Q4: Social role (primary: 12, 13, 14, 15)
    [
        ("Тот, кто вдохновляет и зажигает", "The one who inspires and ignites",
         {12: 3, 17: 2, 7: 1}),
        ("Тот, кто слушает и понимает", "The one who listens and understands",
         {13: 3, 9: 2, 3: 1}),
        ("Тот, кто ведёт и структурирует", "The one who leads and structures",
         {14: 3, 4: 2, 5: 1}),
        ("Тот, кто заботится и поддерживает", "The one who cares and supports",
         {15: 3, 6: 2, 21: 1}),
    ],
    # Q5: How you handle change (primary: 16, 17, 18, 19)
    [
        ("Принимаю с радостью — перемены это рост", "I welcome it with joy — change is growth",
         {16: 3, 10: 2, 12: 1}),
        ("Сопротивляюсь, но потом адаптируюсь", "I resist, but then adapt",
         {17: 3, 12: 2, 15: 1}),
        ("Ищу скрытый смысл в происходящем", "I look for hidden meaning in what happens",
         {18: 3, 2: 2, 9: 1}),
        ("Строю опору, чтобы удержаться на плаву", "I build a foothold to stay afloat",
         {19: 3, 8: 2, 4: 1}),
    ],
    # Q6: Source of inner support (primary: 20, 21, 16, 18)
    [
        ("Вера в себя и свой путь", "Faith in myself and my path",
         {20: 3, 1: 2, 16: 1}),
        ("Любовь близких и связь с ними", "Love of those close to me and connection with them",
         {21: 3, 3: 2, 18: 1}),
        ("Мудрость, опыт и внутренний стержень", "Wisdom, experience, and an inner core",
         {16: 3, 9: 2, 11: 1}),
        ("Мечты, надежда и вдохновение", "Dreams, hope, and inspiration",
         {18: 3, 17: 2, 14: 1}),
    ],
]

# Full descriptions for all 22 Major Arcana
ARCANA_DESCRIPTIONS: dict[int, dict[str, dict[str, str]]] = {
    0: {
        "ru": {
            "name": "Шут",
            "archetype": "Беззаботный искатель",
            "strength": "Способность доверять жизни и делать шаг в неизвестность",
            "shadow": "Безрассудство, избегание ответственности",
            "task": "Научиться сочетать спонтанность с осознанностью",
            "motto": "Путь начинается с первого шага",
            "question": "Куда ты пойдёшь, если отпустишь страх ошибки?",
        },
        "en": {
            "name": "The Fool",
            "archetype": "The carefree seeker",
            "strength": "Ability to trust life and step into the unknown",
            "shadow": "Recklessness, avoiding responsibility",
            "task": "Learn to balance spontaneity with awareness",
            "motto": "The journey begins with the first step",
            "question": "Where will you go if you let go of the fear of mistakes?",
        },
    },
    1: {
        "ru": {
            "name": "Маг",
            "archetype": "Творец реальности",
            "strength": "Умение превращать мысль в действие и управлять ресурсами",
            "shadow": "Манипуляции, желание контролировать всё",
            "task": "Осознать свою силу и направить её на созидание",
            "motto": "Всё необходимое уже в твоих руках",
            "question": "Что ты создашь, если поверишь в свои возможности?",
        },
        "en": {
            "name": "The Magician",
            "archetype": "Creator of reality",
            "strength": "Skill to turn thought into action and manage resources",
            "shadow": "Manipulation, desire to control everything",
            "task": "Realize your power and direct it toward creation",
            "motto": "Everything you need is already in your hands",
            "question": "What will you create if you believe in your abilities?",
        },
    },
    2: {
        "ru": {
            "name": "Верховная Жрица",
            "archetype": "Хранительница тайн",
            "strength": "Глубокая интуиция и способность видеть скрытое",
            "shadow": "Изоляция в мире иллюзий, отрыв от реальности",
            "task": "Научиться делиться своей глубиной с миром",
            "motto": "Ответы внутри — доверься тишине",
            "question": "Что ты видишь, когда закрываешь глаза?",
        },
        "en": {
            "name": "The High Priestess",
            "archetype": "Keeper of secrets",
            "strength": "Deep intuition and ability to see the hidden",
            "shadow": "Isolation in a world of illusions, detachment from reality",
            "task": "Learn to share your depth with the world",
            "motto": "The answers are within — trust the silence",
            "question": "What do you see when you close your eyes?",
        },
    },
    3: {
        "ru": {
            "name": "Императрица",
            "archetype": "Питающая сила",
            "strength": "Способность создавать, заботиться и взращивать",
            "shadow": "Чрезмерная опека, зависимость от одобрения",
            "task": "Научиться заботиться о себе не меньше, чем о других",
            "motto": "Изобилие начинается с принятия",
            "question": "Что в твоей жизни нуждается в питании прямо сейчас?",
        },
        "en": {
            "name": "The Empress",
            "archetype": "Nurturing force",
            "strength": "Ability to create, care, and cultivate",
            "shadow": "Excessive care, dependence on approval",
            "task": "Learn to care for yourself no less than for others",
            "motto": "Abundance begins with acceptance",
            "question": "What in your life needs nourishment right now?",
        },
    },
    4: {
        "ru": {
            "name": "Император",
            "archetype": "Строитель порядка",
            "strength": "Способность создавать структуру и брать ответственность",
            "shadow": "Жёсткость, потребность всё контролировать",
            "task": "Научиться быть опорой, а не тираном",
            "motto": "Порядок рождается из ответственности",
            "question": "Где тебе нужна структура, а где — свобода от неё?",
        },
        "en": {
            "name": "The Emperor",
            "archetype": "Builder of order",
            "strength": "Ability to create structure and take responsibility",
            "shadow": "Rigidity, need to control everything",
            "task": "Learn to be a support, not a tyrant",
            "motto": "Order is born from responsibility",
            "question": "Where do you need structure, and where do you need freedom from it?",
        },
    },
    5: {
        "ru": {
            "name": "Иерофант",
            "archetype": "Мост между мирами",
            "strength": "Мудрость традиций и способность передавать знания",
            "shadow": "Догматизм, слепое следование правилам",
            "task": "Найти свой путь, не отрицая корней",
            "motto": "Учись у прошлого — строй своё будущее",
            "question": "Чей голос звучит в твоих убеждениях?",
        },
        "en": {
            "name": "The Hierophant",
            "archetype": "Bridge between worlds",
            "strength": "Wisdom of traditions and ability to pass on knowledge",
            "shadow": "Dogmatism, blind following of rules",
            "task": "Find your path without denying your roots",
            "motto": "Learn from the past — build your future",
            "question": "Whose voice speaks in your beliefs?",
        },
    },
    6: {
        "ru": {
            "name": "Влюблённые",
            "archetype": "Союз противоположностей",
            "strength": "Способность к глубокой связи и осознанному выбору",
            "shadow": "Зависимость, страх сделать выбор",
            "task": "Научиться выбирать сердцем, не теряя себя",
            "motto": "Любовь — это выбор, который мы делаем каждый день",
            "question": "Что ты выбираешь, когда никто не смотрит?",
        },
        "en": {
            "name": "The Lovers",
            "archetype": "Union of opposites",
            "strength": "Capacity for deep connection and conscious choice",
            "shadow": "Dependence, fear of making a choice",
            "task": "Learn to choose with your heart without losing yourself",
            "motto": "Love is the choice we make every day",
            "question": "What do you choose when no one is watching?",
        },
    },
    7: {
        "ru": {
            "name": "Колесница",
            "archetype": "Покоритель дорог",
            "strength": "Воля, целеустремлённость и умение двигаться вперёд",
            "shadow": "Бесцельная суета, агрессия",
            "task": "Найти направление для своей энергии",
            "motto": "Движение — это жизнь, но важно знать куда",
            "question": "Куда ты двигаешься — и зачем?",
        },
        "en": {
            "name": "The Chariot",
            "archetype": "Conqueror of roads",
            "strength": "Will, determination, and ability to move forward",
            "shadow": "Aimless bustle, aggression",
            "task": "Find a direction for your energy",
            "motto": "Movement is life, but it matters where",
            "question": "Where are you moving — and why?",
        },
    },
    8: {
        "ru": {
            "name": "Сила",
            "archetype": "Мягкая мощь",
            "strength": "Способность побеждать через терпение и внутренний стержень",
            "shadow": "Подавленный гнев, неуверенность",
            "task": "Научиться быть сильным через мягкость",
            "motto": "Истинная сила не кричит",
            "question": "Где твоя сила работает мягко, а где — жёстко?",
        },
        "en": {
            "name": "Strength",
            "archetype": "Gentle power",
            "strength": "Ability to win through patience and inner core",
            "shadow": "Suppressed anger, self-doubt",
            "task": "Learn to be strong through gentleness",
            "motto": "True strength does not shout",
            "question": "Where does your strength work softly, and where does it work hard?",
        },
    },
    9: {
        "ru": {
            "name": "Отшельник",
            "archetype": "Искатель истины",
            "strength": "Способность к уединению, рефлексии и мудрости",
            "shadow": "Изоляция, побег от людей",
            "task": "Находить смысл в тишине и делиться им с миром",
            "motto": "Тишина — это не пустота, а полнота",
            "question": "Что ты находишь, когда остаёшься один?",
        },
        "en": {
            "name": "The Hermit",
            "archetype": "Seeker of truth",
            "strength": "Capacity for solitude, reflection, and wisdom",
            "shadow": "Isolation, escape from people",
            "task": "Find meaning in silence and share it with the world",
            "motto": "Silence is not emptiness, but fullness",
            "question": "What do you find when you are alone?",
        },
    },
    10: {
        "ru": {
            "name": "Колесо Фортуны",
            "archetype": "Танец циклов",
            "strength": "Умение чувствовать ритм жизни и принимать перемены",
            "shadow": "Пассивность, ожидание «судьбы»",
            "task": "Научиться участвовать в своём цикле, а не просто наблюдать",
            "motto": "Колесо поворачивается — важно быть в движении",
            "question": "Какому циклу в твоей жизни пора повернуться?",
        },
        "en": {
            "name": "Wheel of Fortune",
            "archetype": "Dance of cycles",
            "strength": "Ability to feel life's rhythm and accept change",
            "shadow": "Passivity, waiting for 'fate'",
            "task": "Learn to participate in your cycle, not just observe it",
            "motto": "The wheel turns — it matters to be in motion",
            "question": "Which cycle in your life is ready to turn?",
        },
    },
    11: {
        "ru": {
            "name": "Справедливость",
            "archetype": "Гармония правды",
            "strength": "Способность видеть суть и принимать взвешенные решения",
            "shadow": "Холодный расчёт, нежелание видеть полутона",
            "task": "Научиться справедливости к себе и другим",
            "motto": "Правда — это не приговор, а путь",
            "question": "Что для тебя важнее — быть правым или быть честным?",
        },
        "en": {
            "name": "Justice",
            "archetype": "Harmony of truth",
            "strength": "Ability to see the essence and make balanced decisions",
            "shadow": "Cold calculation, unwillingness to see nuance",
            "task": "Learn fairness toward yourself and others",
            "motto": "Truth is not a verdict, but a path",
            "question": "What matters more to you — to be right or to be honest?",
        },
    },
    12: {
        "ru": {
            "name": "Повешенный",
            "archetype": "Пауза перед прозрением",
            "strength": "Способность остановиться и увидеть мир под другим углом",
            "shadow": "Жертвенность без смысла, застревание",
            "task": "Научиться отпускать ради осознанного выбора",
            "motto": "Иногда нужно остановиться, чтобы увидеть путь",
            "question": "Что изменится, если отпустить привычную точку зрения?",
        },
        "en": {
            "name": "The Hanged Man",
            "archetype": "Pause before insight",
            "strength": "Ability to stop and see the world from a different angle",
            "shadow": "Meaningless sacrifice, getting stuck",
            "task": "Learn to let go for a conscious choice",
            "motto": "Sometimes you need to stop to see the path",
            "question": "What changes if you let go of the familiar perspective?",
        },
    },
    13: {
        "ru": {
            "name": "Смерть",
            "archetype": "Трансформация",
            "strength": "Способность отпускать старое и возрождаться",
            "shadow": "Страх перемен, цепляние за прошлое",
            "task": "Принять, что конец — это всегда начало",
            "motto": "Чтобы родиться заново, нужно умереть для старого",
            "question": "Что в твоей жизни уже уходит — и чему это открывает путь?",
        },
        "en": {
            "name": "Death",
            "archetype": "Transformation",
            "strength": "Ability to let go of the old and be reborn",
            "shadow": "Fear of change, clinging to the past",
            "task": "Accept that an ending is always a beginning",
            "motto": "To be reborn, you must die to the old",
            "question": "What in your life is already leaving — and what is it making way for?",
        },
    },
    14: {
        "ru": {
            "name": "Умеренность",
            "archetype": "Золотая середина",
            "strength": "Способность находить баланс и смешивать противоположности",
            "shadow": "Крайности, потеря меры",
            "task": "Научиться терпению и гармонии в мелочах",
            "motto": "Мудрость — в умении находить середину",
            "question": "Где тебе нужна пауза, а где — движение?",
        },
        "en": {
            "name": "Temperance",
            "archetype": "The golden mean",
            "strength": "Ability to find balance and blend opposites",
            "shadow": "Extremes, loss of measure",
            "task": "Learn patience and harmony in small things",
            "motto": "Wisdom is the ability to find the middle",
            "question": "Where do you need a pause, and where do you need movement?",
        },
    },
    15: {
        "ru": {
            "name": "Дьявол",
            "archetype": "Тень и привязанности",
            "strength": "Способность видеть свои зависимости и тень",
            "shadow": "Плен желаний, отрицание своей тени",
            "task": "Научиться осознавать свои цепи и выбирать свободу",
            "motto": "Тень — это не враг, а учитель",
            "question": "Что даёт тебе иллюзию безопасности — и что она стоит?",
        },
        "en": {
            "name": "The Devil",
            "archetype": "Shadow and attachments",
            "strength": "Ability to see your dependencies and shadow",
            "shadow": "Captivity of desires, denial of your shadow",
            "task": "Learn to recognize your chains and choose freedom",
            "motto": "The shadow is not an enemy, but a teacher",
            "question": "What gives you the illusion of safety — and what does it cost?",
        },
    },
    16: {
        "ru": {
            "name": "Башня",
            "archetype": "Внезапная перестройка",
            "strength": "Способность пережить крах и увидеть правду",
            "shadow": "Сопротивление неизбежным переменам",
            "task": "Принять, что рушится то, что было ложным",
            "motto": "Крах — это не конец, а освобождение",
            "question": "Что в твоей жизни нуждается в честной перестройке?",
        },
        "en": {
            "name": "The Tower",
            "archetype": "Sudden overhaul",
            "strength": "Ability to survive collapse and see the truth",
            "shadow": "Resistance to inevitable change",
            "task": "Accept that what was false is crumbling",
            "motto": "Collapse is not an end, but liberation",
            "question": "What in your life needs an honest rebuild?",
        },
    },
    17: {
        "ru": {
            "name": "Звезда",
            "archetype": "Свет надежды",
            "strength": "Способность верить, вдохновлять и исцелять",
            "shadow": "Наивность, разочарование",
            "task": "Научиться держать свет, даже когда веры мало",
            "motto": "Звезда светит даже в самой тёмной ночи",
            "question": "На что ты возлагаешь надежду — и что её подпитывает?",
        },
        "en": {
            "name": "The Star",
            "archetype": "Light of hope",
            "strength": "Ability to believe, inspire, and heal",
            "shadow": "Naivety, disillusionment",
            "task": "Learn to hold the light even when faith runs low",
            "motto": "The star shines even in the darkest night",
            "question": "What do you place your hope in — and what feeds it?",
        },
    },
    18: {
        "ru": {
            "name": "Луна",
            "archetype": "Путешественник по иллюзиям",
            "strength": "Сapacity to navigate uncertainty and trust the subconscious",
            "shadow": "Тревоги, страхи, блуждание в тумане",
            "task": "Научиться различать интуицию и тревогу",
            "motto": "Туман рассеивается для тех, кто не боится идти",
            "question": "Какая иллюзия сейчас рассеивается в твоей жизни?",
        },
        "en": {
            "name": "The Moon",
            "archetype": "Traveler through illusions",
            "strength": "Capacity to navigate uncertainty and trust the subconscious",
            "shadow": "Anxieties, fears, wandering in the fog",
            "task": "Learn to distinguish intuition from anxiety",
            "motto": "The fog clears for those who are not afraid to walk",
            "question": "What illusion is clearing in your life right now?",
        },
    },
    19: {
        "ru": {
            "name": "Солнце",
            "archetype": "Радость и ясность",
            "strength": "Способность светить, радоваться и быть в моменте",
            "shadow": "Избегание тени, навязчивая позитивность",
            "task": "Научиться принимать и свет, и тень",
            "motto": "Ясность приходит к тем, кто не боится света",
            "question": "Что в твоей жизни заслуживает чистой радости?",
        },
        "en": {
            "name": "The Sun",
            "archetype": "Joy and clarity",
            "strength": "Ability to shine, rejoice, and be in the moment",
            "shadow": "Avoiding shadow, forced positivity",
            "task": "Learn to accept both light and shadow",
            "motto": "Clarity comes to those who are not afraid of the light",
            "question": "What in your life deserves pure joy?",
        },
    },
    20: {
        "ru": {
            "name": "Суд",
            "archetype": "Пробуждение к зову",
            "strength": "Способность услышать свой внутренний зов и ответить",
            "shadow": "Самоосуждение, страх перемен",
            "task": "Научиться прощать себя и двигаться дальше",
            "motto": "Каждый конец — это новое призвание",
            "question": "Какой внутренний призыв ты слышишь — и что мешает ответить?",
        },
        "en": {
            "name": "Judgement",
            "archetype": "Awakening to the call",
            "strength": "Ability to hear your inner calling and answer it",
            "shadow": "Self-judgment, fear of change",
            "task": "Learn to forgive yourself and move on",
            "motto": "Every ending is a new calling",
            "question": "What inner call do you hear — and what stands in the way of answering?",
        },
    },
    21: {
        "ru": {
            "name": "Мир",
            "archetype": "Целостность и завершение",
            "strength": "Сapacity to see the whole picture and celebrate completion",
            "shadow": "Незавершённость, страх закрыть главу",
            "task": "Научиться отпускать и начинать новый цикл",
            "motto": "Завершение — это не конец, а начало нового круга",
            "question": "Какой цикл завершается — и чему ты научился?",
        },
        "en": {
            "name": "The World",
            "archetype": "Wholeness and completion",
            "strength": "Capacity to see the whole picture and celebrate completion",
            "shadow": "Incompleteness, fear of closing a chapter",
            "task": "Learn to let go and begin a new cycle",
            "motto": "Completion is not an end, but the beginning of a new circle",
            "question": "What cycle is closing — and what have you learned?",
        },
    },
}


def compute_result(answers: list[int]) -> int:
    """Compute the winning Arcana from a list of answer indices (0-3 per question).

    Each answer gives weight to multiple Arcana. The Arcana with the highest total
    weight wins. Ties are broken by the lower Arcana number (deterministic).
    """
    scores: dict[int, int] = {}
    for q_idx, a_idx in enumerate(answers):
        if q_idx >= len(QUIZ_QUESTIONS):
            break
        question = QUIZ_QUESTIONS[q_idx]
        if a_idx >= len(question):
            continue
        _, _, weights = question[a_idx]
        for arcana, weight in weights.items():
            scores[arcana] = scores.get(arcana, 0) + weight

    if not scores:
        return 0

    # Find max score; ties broken by lower Arcana number
    max_score = max(scores.values())
    candidates = [a for a, s in scores.items() if s == max_score]
    return min(candidates)


def get_arcana_description(arcana_num: int, lang: str) -> dict[str, str]:
    """Return the full description of an Arcana in the given language."""
    desc = ARCANA_DESCRIPTIONS.get(arcana_num, {})
    return desc.get(lang, desc.get("ru", {}))


def format_arcana_result(arcana_num: int, lang: str) -> str:
    """Format the Arcana result as a readable text."""
    desc = get_arcana_description(arcana_num, lang)
    if not desc:
        return ""

    if lang == "ru":
        return (
            f"<b>{desc.get('name', '')}</b>\n"
            f"<i>{desc.get('archetype', '')}</i>\n\n"
            f"Сильная сторона: {desc.get('strength', '')}\n"
            f"Теневая сторона: {desc.get('shadow', '')}\n"
            f"Текущая задача: {desc.get('task', '')}\n\n"
            f"Девиз: {desc.get('motto', '')}\n"
            f"✦ {desc.get('question', '')}"
        )
    else:
        return (
            f"<b>{desc.get('name', '')}</b>\n"
            f"<i>{desc.get('archetype', '')}</i>\n\n"
            f"Strength: {desc.get('strength', '')}\n"
            f"Shadow: {desc.get('shadow', '')}\n"
            f"Current task: {desc.get('task', '')}\n\n"
            f"Motto: {desc.get('motto', '')}\n"
            f"✦ {desc.get('question', '')}"
        )
