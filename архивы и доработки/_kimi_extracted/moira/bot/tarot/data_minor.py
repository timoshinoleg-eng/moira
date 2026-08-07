from __future__ import annotations

SUITS = {
    "wands": {
        "ru": "Жезлы", "ru_gen": "Жезлов", "en": "Wands",
        "ru_theme": "действия, амбиции и энергия",
        "en_theme": "action, ambition and energy",
        "kw_ru": ["действие", "вдохновение", "энергия"],
        "kw_en": ["action", "inspiration", "drive"],
    },
    "cups": {
        "ru": "Кубки", "ru_gen": "Кубков", "en": "Cups",
        "ru_theme": "чувства, отношения и интуиция",
        "en_theme": "feelings, relationships and intuition",
        "kw_ru": ["эмоции", "отношения", "интуиция"],
        "kw_en": ["emotions", "relationships", "intuition"],
    },
    "swords": {
        "ru": "Мечи", "ru_gen": "Мечей", "en": "Swords",
        "ru_theme": "мысли, решения и слова",
        "en_theme": "thoughts, decisions and words",
        "kw_ru": ["мысли", "решения", "конфликт"],
        "kw_en": ["thoughts", "decisions", "conflict"],
    },
    "pentacles": {
        "ru": "Пентакли", "ru_gen": "Пентаклей", "en": "Pentacles",
        "ru_theme": "деньги, работа и материальный мир",
        "en_theme": "money, work and the material world",
        "kw_ru": ["деньги", "работа", "ресурсы"],
        "kw_en": ["money", "work", "resources"],
    },
}

RANK_NAMES_RU = {
    "ace": "Туз", "two": "Двойка", "three": "Тройка", "four": "Четвёрка",
    "five": "Пятёрка", "six": "Шестёрка", "seven": "Семёрка", "eight": "Восьмёрка",
    "nine": "Девятка", "ten": "Десятка",
}
RANK_NAMES_EN = {
    "ace": "Ace", "two": "Two", "three": "Three", "four": "Four",
    "five": "Five", "six": "Six", "seven": "Seven", "eight": "Eight",
    "nine": "Nine", "ten": "Ten",
}
COURT_NAMES_RU = {"page": "Паж", "knight": "Рыцарь", "queen": "Королева", "king": "Король"}
COURT_NAMES_EN = {"page": "Page", "knight": "Knight", "queen": "Queen", "king": "King"}

# Suit-specific variations for each rank to make 56 minor cards unique
RANK_SUIT_VARIANTS = {
    "ace": {
        "wands": {
            "ru_upr": "Искра замысла: в руках появляется шанс начать что-то яркое и страстное ({theme}).",
            "ru_rev": "Замысел гаснет в руках; не хватает рычагов или смелости разжечь огонь ({theme}).",
            "en_upr": "A spark of purpose: a chance to begin something bold and passionate lands in your hands ({theme}).",
            "en_rev": "The idea dies in your grip — you lack the leverage or the nerve to strike the match ({theme}).",
        },
        "cups": {
            "ru_upr": "Эмоции переполняют чашу: новый эмоциональный опыт готов войти в жизнь ({theme}).",
            "ru_rev": "Чаша пуста или закрыта: чувства не находят выхода из-за обиды или страха ({theme}).",
            "en_upr": "Emotions brim over: a new emotional experience is ready to enter your life ({theme}).",
            "en_rev": "The cup is empty or shut: feeling is blocked by resentment or fear ({theme}).",
        },
        "swords": {
            "ru_upr": "Прозрение: в голову приходит ясная мысль, открывающая путь ({theme}).",
            "ru_rev": "Иллюзия ясности: голова кружится, но решение пока не созрело ({theme}).",
            "en_upr": "A flash of insight: a clear thought breaks through and opens the way ({theme}).",
            "en_rev": "An illusion of clarity: your head spins, but the decision is not yet ripe ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Первый заработок, контракт, материальная возможность ({theme}).",
            "ru_rev": "Шанс упущен из-за невнимательности или страха перед риском ({theme}).",
            "en_upr": "A first earning, a contract, a material opportunity ({theme}).",
            "en_rev": "An opportunity missed through inattention or fear of risk ({theme}).",
        },
    },
    "two": {
        "wands": {
            "ru_upr": "Партнёрство или выбор направления: два пути требуют соразмерности ({theme}).",
            "ru_rev": "Метание между двумя целями, нет чувства меры ({theme}).",
            "en_upr": "Partnership or a choice of direction: two paths call for balance ({theme}).",
            "en_rev": "Torn between two goals, a sense of proportion is lost ({theme}).",
        },
        "cups": {
            "ru_upr": "Взаимная симпатия или договорённость: связь начинает крепнуть ({theme}).",
            "ru_rev": "Разлад, недоверие или игра в одни ворота ({theme}).",
            "en_upr": "Mutual attraction or an agreement: the bond begins to strengthen ({theme}).",
            "en_rev": "Disharmony, distrust, or a one-sided effort ({theme}).",
        },
        "swords": {
            "ru_upr": "Тупик: две правды не дают друг другу шанса ({theme}).",
            "ru_rev": "Выход из тупика; одна из сторон отступает ({theme}).",
            "en_upr": "A stalemate: two truths deny each other a chance ({theme}).",
            "en_rev": "A way out of the deadlock; one side gives way ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Гибкость в ресурсах: приходится жонглировать расходами и доходами ({theme}).",
            "ru_rev": "Дисбаланс бюджета: доходы не поспевают за тратами ({theme}).",
            "en_upr": "Resource flexibility: juggling expenses and income ({theme}).",
            "en_rev": "Budget imbalance: income cannot keep up with spending ({theme}).",
        },
    },
    "three": {
        "wands": {
            "ru_upr": "Первые плоды усилий: расширение горизонтов и выход на новый уровень ({theme}).",
            "ru_rev": "Задержка в развитии; результаты пока тонут в деталях ({theme}).",
            "en_upr": "First fruits of effort: horizons expand and a new level beckons ({theme}).",
            "en_rev": "A delay in progress; results are still lost in the details ({theme}).",
        },
        "cups": {
            "ru_upr": "Радость и товарищество: время разделить счастье с близкими ({theme}).",
            "ru_rev": "Одиночество в толпе; радость не достигает сердца ({theme}).",
            "en_upr": "Joy and fellowship: a time to share happiness with those close to you ({theme}).",
            "en_rev": "Loneliness in a crowd; joy does not reach the heart ({theme}).",
        },
        "swords": {
            "ru_upr": "Пронзительная боль правды: мысль ранит, но освобождает ({theme}).",
            "ru_rev": "Рана начинает затягиваться; горечь слова ослабевает ({theme}).",
            "en_upr": "The piercing pain of truth: the thought cuts, but sets free ({theme}).",
            "en_rev": "The wound begins to heal; the bitterness of the word fades ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Признание мастерства: первая награда за качественную работу ({theme}).",
            "ru_rev": "Работа есть, а признания нет; усилия не оценены ({theme}).",
            "en_upr": "Recognition of skill: the first reward for quality work ({theme}).",
            "en_rev": "The work is there, the recognition is not; effort goes unseen ({theme}).",
        },
    },
    "four": {
        "wands": {
            "ru_upr": "Праздник и тёплая встреча: опора в кругу единомышленников ({theme}).",
            "ru_rev": "Временное отчуждение; радость не находит точки опоры ({theme}).",
            "en_upr": "A celebration and a warm meeting: support among kindred spirits ({theme}).",
            "en_rev": "A temporary estrangement; joy finds no foothold ({theme}).",
        },
        "cups": {
            "ru_upr": "Апатия и самопогружение: карты лежат перед глазами, но не доходят ({theme}).",
            "ru_rev": "Поворот к миру: взгляд замечает новые возможности ({theme}).",
            "en_upr": "Apathy and self-absorption: the cards lie in view but do not reach you ({theme}).",
            "en_rev": "A turn toward the world: the eye spots new possibilities ({theme}).",
        },
        "swords": {
            "ru_upr": "Передышка и восстановление: мысли упорядочены ({theme}).",
            "ru_rev": "Насильный отдых; мысли крутятся, не давая покоя ({theme}).",
            "en_upr": "A pause and recovery: thoughts are set in order ({theme}).",
            "en_rev": "A forced rest; thoughts churn and bring no peace ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Крепкая хватка за ресурсы: стабильность превращается в жадность ({theme}).",
            "ru_rev": "Излишняя щедрость или страх потери; ресурсы утекают ({theme}).",
            "en_upr": "A tight grip on resources: stability slides into greed ({theme}).",
            "en_rev": "Excessive generosity or fear of loss; resources slip away ({theme}).",
        },
    },
    "five": {
        "wands": {
            "ru_upr": "Состязание и конфликт: борьба идёт за место под солнцем ({theme}).",
            "ru_rev": "Выход из борьбы: либо усталость, либо перемирие ({theme}).",
            "en_upr": "Competition and conflict: a fight for a place in the sun ({theme}).",
            "en_rev": "An exit from the fight: either fatigue or a truce ({theme}).",
        },
        "cups": {
            "ru_upr": "Потеря одного ради сохранения остального: из трёх кубков два стоят ({theme}).",
            "ru_rev": "Поворот к утраченному; появляется шанс восстановить ({theme}).",
            "en_upr": "Losing one to save the rest: two of the three cups still stand ({theme}).",
            "en_rev": "A turn toward what was lost; a chance to rebuild appears ({theme}).",
        },
        "swords": {
            "ru_upr": "Пиррова победа: выиграв, теряешь часть себя ({theme}).",
            "ru_rev": "Освободительное поражение: конфликт закрыт, но с потерями ({theme}).",
            "en_upr": "A Pyrrhic victory: winning costs you part of yourself ({theme}).",
            "en_rev": "A liberating defeat: the conflict closes, but with losses ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Материальные трудности: ощущение изоляции и нехватки ({theme}).",
            "ru_rev": "Выход из кризиса; помощь приходит с неожиданной стороны ({theme}).",
            "en_upr": "Material hardship: a sense of isolation and scarcity ({theme}).",
            "en_rev": "A way out of the crisis; help arrives from an unexpected side ({theme}).",
        },
    },
    "six": {
        "wands": {
            "ru_upr": "Общественное признание: маленькая победа на виду у всех ({theme}).",
            "ru_rev": "Отложенное признание; триумф не ощущается ({theme}).",
            "en_upr": "Public recognition: a small victory in full view ({theme}).",
            "en_rev": "Delayed recognition; the triumph is not felt ({theme}).",
        },
        "cups": {
            "ru_upr": "Возврат к прошлому: воспоминания, корни, наследие ({theme}).",
            "ru_rev": "Зависание в прошлом; надо учиться отпускать ({theme}).",
            "en_upr": "A return to the past: memories, roots, heritage ({theme}).",
            "en_rev": "Stuck in the past; learning to let go is needed ({theme}).",
        },
        "swords": {
            "ru_upr": "Медленное движение к спокойствию: переход на берег ({theme}).",
            "ru_rev": "Застревание в переходном состоянии; течение относит прочь ({theme}).",
            "en_upr": "A slow drift toward calm: moving to the shore ({theme}).",
            "en_rev": "Stuck in transition; the current carries you away ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Щедрость и поддержка: баланс между давать и получать ({theme}).",
            "ru_rev": "Неравный обмен: одному даётся больше, чем другому ({theme}).",
            "en_upr": "Generosity and support: a balance between giving and receiving ({theme}).",
            "en_rev": "An unequal exchange: one gives more than the other receives ({theme}).",
        },
    },
    "seven": {
        "wands": {
            "ru_upr": "Защита своих позиций: стойкость под давлением ({theme}).",
            "ru_rev": "Оборона рушится; давление становится невыносимым ({theme}).",
            "en_upr": "Defending your ground: resilience under pressure ({theme}).",
            "en_rev": "The defence crumbles; the pressure becomes unbearable ({theme}).",
        },
        "cups": {
            "ru_upr": "Иллюзии и соблазны: семь чаш — семь возможностей, не все реальны ({theme}).",
            "ru_rev": "Иллюзии рассеиваются; приоритеты становятся ясны ({theme}).",
            "en_upr": "Illusions and temptations: seven cups — seven possibilities, not all real ({theme}).",
            "en_rev": "Illusions clear; priorities come into focus ({theme}).",
        },
        "swords": {
            "ru_upr": "Хитрость и обходной путь: один уходит с добычей ({theme}).",
            "ru_rev": "Разоблачение; тайное становится явным ({theme}).",
            "en_upr": "Cunning and a detour: one leaves with the prize ({theme}).",
            "en_rev": "Exposure; the hidden becomes visible ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Ожидание урожая: инвестиции требуют терпения ({theme}).",
            "ru_rev": "Преждевременная остановка; урожай не оправдал ожиданий ({theme}).",
            "en_upr": "Waiting for the harvest: investments demand patience ({theme}).",
            "en_rev": "A premature halt; the harvest falls short of expectations ({theme}).",
        },
    },
    "eight": {
        "wands": {
            "ru_upr": "Стремительное движение: стрелы летят к цели ({theme}).",
            "ru_rev": "Задержка в пути; стрелы зависли в воздухе ({theme}).",
            "en_upr": "Swift motion: arrows fly toward the goal ({theme}).",
            "en_rev": "A delay on the road; arrows hang in the air ({theme}).",
        },
        "cups": {
            "ru_upr": "Уход в поисках чего-то большего: стабильное оставлено ради неизвестного ({theme}).",
            "ru_rev": "Поворот назад; возвращение к тому, что было оставлено ({theme}).",
            "en_upr": "Leaving to seek something greater: the stable is left for the unknown ({theme}).",
            "en_rev": "A turn back; a return to what was left behind ({theme}).",
        },
        "swords": {
            "ru_upr": "Ловушка ума: слова и правила связывают по рукам и ногам ({theme}).",
            "ru_rev": "Освобождение от оков; пелена спадает с глаз ({theme}).",
            "en_upr": "A trap of the mind: words and rules bind hand and foot ({theme}).",
            "en_rev": "Breaking free of the bonds; the veil lifts from the eyes ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Усердная работа на результат: мастерство растёт с каждым повторением ({theme}).",
            "ru_rev": "Рутина без роста; работа идёт, но не приносит удовлетворения ({theme}).",
            "en_upr": "Diligent work for results: skill grows with every repetition ({theme}).",
            "en_rev": "Routine without growth; the work goes on but brings no satisfaction ({theme}).",
        },
    },
    "nine": {
        "wands": {
            "ru_upr": "Стойкость после испытаний: усталость есть, но позиция держится ({theme}).",
            "ru_rev": "Измотанность; защита трещит по швам ({theme}).",
            "en_upr": "Resilience after trials: fatigue is there, but the position holds ({theme}).",
            "en_rev": "Exhaustion; the defence is cracking at the seams ({theme}).",
        },
        "cups": {
            "ru_upr": "Удовлетворение и комфорт: желания исполнены ({theme}).",
            "ru_rev": "Пресыщение; радости становится слишком много ({theme}).",
            "en_upr": "Satisfaction and comfort: wishes are fulfilled ({theme}).",
            "en_rev": "Satiety; joy becomes too much ({theme}).",
        },
        "swords": {
            "ru_upr": "Тревога и бессонница: мысли не дают уснуть ({theme}).",
            "ru_rev": "Тревога отступает; ночь проясняется ({theme}).",
            "en_upr": "Anxiety and sleeplessness: thoughts keep you awake ({theme}).",
            "en_rev": "Anxiety recedes; the night clears ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Материальная независимость: плоды усилий налицо ({theme}).",
            "ru_rev": "Зависимость от внешнего; комфорт не приносит свободы ({theme}).",
            "en_upr": "Material independence: the fruits of effort are evident ({theme}).",
            "en_rev": "Dependence on the outside; comfort does not bring freedom ({theme}).",
        },
    },
    "ten": {
        "wands": {
            "ru_upr": "Перегрузка: на плечах слишком много обязательств ({theme}).",
            "ru_rev": "Освобождение от части ноши; пора делегировать ({theme}).",
            "en_upr": "Overload: too many burdens on the shoulders ({theme}).",
            "en_rev": "A release from part of the load; time to delegate ({theme}).",
        },
        "cups": {
            "ru_upr": "Семейное счастье и гармония: дом наполнен теплом ({theme}).",
            "ru_rev": "Разлад в близком кругу; гармония нарушена ({theme}).",
            "en_upr": "Family happiness and harmony: the home is filled with warmth ({theme}).",
            "en_rev": "Discord in the inner circle; harmony is broken ({theme}).",
        },
        "swords": {
            "ru_upr": "Критическая точка: падение достигло дна ({theme}).",
            "ru_rev": "Поворот вспять; худшее позади ({theme}).",
            "en_upr": "A critical point: the fall has hit the bottom ({theme}).",
            "en_rev": "A turn for the better; the worst is behind ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Долгосрочное благополучие: фундамент для будущих поколений ({theme}).",
            "ru_rev": "Хрупкость благополучия; наследие под угрозой ({theme}).",
            "en_upr": "Long-term prosperity: a foundation for future generations ({theme}).",
            "en_rev": "The fragility of prosperity; the legacy is under threat ({theme}).",
        },
    },
}

COURT_SUIT_VARIANTS = {
    "page": {
        "wands": {
            "ru_upr": "Вестник новых начинаний: весть о шансе или проекте ({theme}).",
            "ru_rev": "Незрелость замысла; вести теряются по пути ({theme}).",
            "en_upr": "A messenger of new beginnings: news of a chance or a project ({theme}).",
            "en_rev": "An immature design; news is lost along the way ({theme}).",
        },
        "cups": {
            "ru_upr": "Романтическая весть: предложение, признание, творческий импульс ({theme}).",
            "ru_rev": "Незрелое чувство; фантазии уводят в сторону ({theme}).",
            "en_upr": "A romantic message: a proposal, a confession, a creative impulse ({theme}).",
            "en_rev": "An immature feeling; fantasies lead astray ({theme}).",
        },
        "swords": {
            "ru_upr": "Любопытство и бдительность: вестник вопросов и разоблачений ({theme}).",
            "ru_rev": "Болтливость без цели; любопытство переходит границы ({theme}).",
            "en_upr": "Curiosity and vigilance: a messenger of questions and exposures ({theme}).",
            "en_rev": "Aimless chatter; curiosity crosses the line ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Ученик дела: новость об учёбе, работе, финансовом шансе ({theme}).",
            "ru_rev": "Несерьёзное отношение к делу; учение впустую ({theme}).",
            "en_upr": "A student of the craft: news of study, work, a financial chance ({theme}).",
            "en_rev": "A frivolous attitude to the craft; learning in vain ({theme}).",
        },
    },
    "knight": {
        "wands": {
            "ru_upr": "Страстный порыв: быстрое движение к цели ({theme}).",
            "ru_rev": "Спешка без направления; выгорание на ходу ({theme}).",
            "en_upr": "A passionate dash: fast movement toward the goal ({theme}).",
            "en_rev": "Rush without direction; burnout on the move ({theme}).",
        },
        "cups": {
            "ru_upr": "Романтический ход: предложение, приглашение, творческий эксперимент ({theme}).",
            "ru_rev": "Пустая романтика; слова расходятся с делом ({theme}).",
            "en_upr": "A romantic move: a proposal, an invitation, a creative experiment ({theme}).",
            "en_rev": "Empty romance; words do not match deeds ({theme}).",
        },
        "swords": {
            "ru_upr": "Резкий напор: мысль превращается в действие мгновенно ({theme}).",
            "ru_rev": "Необдуманный удар; поспешность ведёт к ошибке ({theme}).",
            "en_upr": "A sharp thrust: thought turns into action instantly ({theme}).",
            "en_rev": "A rash blow; haste leads to error ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Надёжный труженик: медленное, но уверенное продвижение ({theme}).",
            "ru_rev": "Застой в делах; работа без продвижения ({theme}).",
            "en_upr": "A reliable worker: slow but steady progress ({theme}).",
            "en_rev": "Stagnation in affairs; work without progress ({theme}).",
        },
    },
    "queen": {
        "wands": {
            "ru_upr": "Тёплая харизма: вдохновляет и ведёт за собой ({theme}).",
            "ru_rev": "Ревность и давление; тепло переходит в жар ({theme}).",
            "en_upr": "Warm charisma: inspires and leads ({theme}).",
            "en_rev": "Jealousy and pressure; warmth turns to heat ({theme}).",
        },
        "cups": {
            "ru_upr": "Глубокая интуиция: чувствует то, что скрыто ({theme}).",
            "ru_rev": "Эмоциональная зависимость; границы размыты ({theme}).",
            "en_upr": "Deep intuition: feels what is hidden ({theme}).",
            "en_rev": "Emotional dependence; boundaries are blurred ({theme}).",
        },
        "swords": {
            "ru_upr": "Ясный ум и честность: правда говорится прямо ({theme}).",
            "ru_rev": "Холодная жестокость; правда ранит без нужды ({theme}).",
            "en_upr": "A clear mind and honesty: truth is told plainly ({theme}).",
            "en_rev": "Cold cruelty; truth wounds without need ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Практичная забота: дом и ресурсы в надёжных руках ({theme}).",
            "ru_rev": "Материальная зависимость; забота превращается в контроль ({theme}).",
            "en_upr": "Practical care: home and resources in reliable hands ({theme}).",
            "en_rev": "Material dependence; care turns into control ({theme}).",
        },
    },
    "king": {
        "wands": {
            "ru_upr": "Вдохновляющий лидер: ведёт за мечтой ({theme}).",
            "ru_rev": "Тирания энтузиазма; давление на окружающих ({theme}).",
            "en_upr": "An inspiring leader: leads toward the dream ({theme}).",
            "en_rev": "A tyranny of enthusiasm; pressure on others ({theme}).",
        },
        "cups": {
            "ru_upr": "Эмоциональная зрелость: управляет чувствами мудро ({theme}).",
            "ru_rev": "Манипуляция чувствами; зрелость переходит в холод ({theme}).",
            "en_upr": "Emotional maturity: manages feelings wisely ({theme}).",
            "en_rev": "Emotional manipulation; maturity turns to coldness ({theme}).",
        },
        "swords": {
            "ru_upr": "Интеллектуальный авторитет: решения взвешены и справедливы ({theme}).",
            "ru_rev": "Интеллектуальное высокомерие; справедливость в пользу силы ({theme}).",
            "en_upr": "An intellectual authority: decisions are balanced and fair ({theme}).",
            "en_rev": "Intellectual arrogance; justice favours the strong ({theme}).",
        },
        "pentacles": {
            "ru_upr": "Материальный успех: стабильность и щедрость ({theme}).",
            "ru_rev": "Жадность и власть; успех ради успеха ({theme}).",
            "en_upr": "Material success: stability and generosity ({theme}).",
            "en_rev": "Greed and power; success for its own sake ({theme}).",
        },
    },
}

# Keep RANK_CORE and COURT_CORE as fallback for generic references
RANK_CORE = {
    "ace": {
        "ru_upr": "Чистое начало: большой потенциал и шанс ({theme}).",
        "ru_rev": "Шанс упущен или заблокирован; начало откладывается ({theme}).",
        "en_upr": "A pure beginning: great potential and a chance ({theme}).",
        "en_rev": "A blocked start; an opportunity postponed ({theme}).",
    },
    "two": {
        "ru_upr": "Первые шаги и баланс: учись совмещать ({theme}).",
        "ru_rev": "Дисбаланс и метание между двумя ({theme}).",
        "en_upr": "First steps and balance: learn to combine ({theme}).",
        "en_rev": "Imbalance, torn between two ({theme}).",
    },
    "three": {
        "ru_upr": "Рост и первые плоды: усилия начинают окупаться ({theme}).",
        "ru_rev": "Задержки в росте; результаты пока слабые ({theme}).",
        "en_upr": "Growth and first fruits: efforts begin to pay off ({theme}).",
        "en_rev": "Delayed growth; results are still weak ({theme}).",
    },
    "four": {
        "ru_upr": "Устойчивость и опора: закрепи достигнутое ({theme}).",
        "ru_rev": "Застой и чрезмерная хватка; стабильность превращается в клетку ({theme}).",
        "en_upr": "Stability and support: consolidate what you've gained ({theme}).",
        "en_rev": "Stagnation and a grip too tight; stability turns into a cage ({theme}).",
    },
    "five": {
        "ru_upr": "Кризис и конфликт: потерянное можно отпустить ({theme}).",
        "ru_rev": "Выход из кризиса; худшее позади ({theme}).",
        "en_upr": "Crisis and conflict: what's lost can be released ({theme}).",
        "en_rev": "Recovery from crisis; the worst is behind ({theme}).",
    },
    "six": {
        "ru_upr": "Гармония и восстановление: приходят помощь и признание ({theme}).",
        "ru_rev": "Дисгармония; помощь запаздывает, рассчитывай на себя ({theme}).",
        "en_upr": "Harmony and recovery: help and recognition arrive ({theme}).",
        "en_rev": "Disharmony; help is slow, rely on yourself ({theme}).",
    },
    "seven": {
        "ru_upr": "Испытание и размышление: время оценить стратегию ({theme}).",
        "ru_rev": "Сомнения и ухищрения; не ищи обходных путей ({theme}).",
        "en_upr": "Trial and reflection: time to assess your strategy ({theme}).",
        "en_rev": "Doubt and tricks; don't look for shortcuts ({theme}).",
    },
    "eight": {
        "ru_upr": "Движение и мастерство: дело набирает скорость ({theme}).",
        "ru_rev": "Задержки и повторение ошибок; темп потерян ({theme}).",
        "en_upr": "Movement and mastery: things gain speed ({theme}).",
        "en_rev": "Delays and repeated mistakes; momentum lost ({theme}).",
    },
    "nine": {
        "ru_upr": "Почти у цели: плод созрел, будь готов собрать урожай ({theme}).",
        "ru_rev": "Страх успеха; результат близко, но что-то мешает его принять ({theme}).",
        "en_upr": "Almost there: the fruit is ripe, be ready to harvest ({theme}).",
        "en_rev": "Fear of success; the result is near but something blocks it ({theme}).",
    },
    "ten": {
        "ru_upr": "Завершение цикла и пик; впереди новый виток ({theme}).",
        "ru_rev": "Перегрузка и тяжёлый финал; пора делегировать и отдыхать ({theme}).",
        "en_upr": "Cycle complete, the peak reached; a new turn ahead ({theme}).",
        "en_rev": "Overload and a heavy ending; time to delegate and rest ({theme}).",
    },
}

COURT_CORE = {
    "page": {
        "ru_upr": "Вестник и ученик: новости, новые навыки и свежий взгляд ({theme}).",
        "ru_rev": "Незрелость и рассеянность; новости задерживаются ({theme}).",
        "en_upr": "A messenger and a learner: news, new skills and a fresh view ({theme}).",
        "en_rev": "Immaturity and distraction; news is delayed ({theme}).",
    },
    "knight": {
        "ru_upr": "Энергичный рывок: дело движется быстро и целенаправленно ({theme}).",
        "ru_rev": "Спешка без плана или выгорание; темп надо пересмотреть ({theme}).",
        "en_upr": "An energetic dash: things move fast and with purpose ({theme}).",
        "en_rev": "Rush without a plan or burnout; rethink the pace ({theme}).",
    },
    "queen": {
        "ru_upr": "Забота и мудрость: тёплая поддержка и эмоциональная зрелость ({theme}).",
        "ru_rev": "Манипуляция чувствами или самопожертвование сверх меры ({theme}).",
        "en_upr": "Care and wisdom: warm support and emotional maturity ({theme}).",
        "en_rev": "Emotional manipulation or excessive self-sacrifice ({theme}).",
    },
    "king": {
        "ru_upr": "Мастерство и авторитет: уверенное лидерство и верные решения ({theme}).",
        "ru_rev": "Авторитарность и давление; сила без гибкости ({theme}).",
        "en_upr": "Mastery and authority: confident leadership and sound decisions ({theme}).",
        "en_rev": "Authoritarianism and pressure; strength without flexibility ({theme}).",
    },
}
