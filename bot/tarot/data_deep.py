"""Position-aware meanings for the 22 Major Arcana (S3 content drop from TASKS_SOL.md).

Six of the ten ``CardMeanings`` fields were declared but never populated. This module
fills three of them: ``inner_state``, ``decision``, ``blocked_expression``.

How each field is meant to be read (see PLAN_WINS.md, M3):

``inner_state``          what the person feels and lacks inside when this card lands in
                         a "your state" role (love/you).
``decision``             which criterion or angle this card offers when a choice is due
                         (choice/criterion, situation/next_step).
``blocked_expression``   what the energy degenerates into when it is not lived out
                         (situation/hidden). This is NOT a repeat of ``shadow``:
                         ``shadow`` is the underside of the card expressing itself,
                         ``blocked_expression`` is what the *unlived* energy becomes.

The content is orientation-neutral, so ``deck.py`` populates it on both the upright and
the reversed ``CardMeanings``. Injecting these into the LLM prompt is M3 proper and must
go through an A/B by PROMPT_VERSION; nothing here changes the prompt by itself.
"""
from __future__ import annotations

MAJOR_DEEP: dict[int, dict[str, dict[str, str]]] = {
    0: {
        "inner_state": {"ru": "Ты чувствуешь лёгкость и готовность шагнуть в новое, но тебе не хватает опоры.", "en": "You feel lightness and readiness to step into something new, but you lack grounding."},
        "decision": {"ru": "Выбирай то, что оставляет место для спонтанности, а не то, что требует жёсткого плана.", "en": "Choose what leaves room for spontaneity rather than demanding a rigid plan."},
        "blocked_expression": {"ru": "Желание начать превращается в бегство от обязательств, когда нет ясного направления.", "en": "The urge to begin turns into running from commitments when there is no clear direction."},
    },
    1: {
        "inner_state": {"ru": "Ты чувствуешь сосредоточенность и доступ к своим способностям, но тебе не хватает ясной цели.", "en": "You feel focused and connected to your abilities, but you lack a clear goal."},
        "decision": {"ru": "Выбирай то, что позволяет тебе применить свои навыки, а не то, что делает тебя пассивным.", "en": "Choose what lets you apply your skills rather than what makes you passive."},
        "blocked_expression": {"ru": "Сила воли превращается в манипуляцию или хитрость, когда нет доверия к процессу.", "en": "Willpower turns into manipulation or cunning when there is no trust in the process."},
    },
    2: {
        "inner_state": {"ru": "Ты чувствуешь глубокую внутреннюю тишину, но тебе не хватает внешнего подтверждения.", "en": "You feel deep inner silence, but you lack external validation."},
        "decision": {"ru": "Выбирай то, что резонирует с твоей интуицией, а не то, что громче всего звучит.", "en": "Choose what resonates with your intuition rather than what is loudest."},
        "blocked_expression": {"ru": "Интуиция превращается в скрытность или отказ делиться знанием, когда её не признают.", "en": "Intuition turns into secrecy or refusal to share knowledge when it is not acknowledged."},
    },
    3: {
        "inner_state": {"ru": "Ты чувствуешь изобилие и желание заботиться, но тебе не хватает границ для себя.", "en": "You feel abundance and a desire to nurture, but you lack boundaries for yourself."},
        "decision": {"ru": "Выбирай то, что питает жизнь, а не то, что истощает тебя.", "en": "Choose what nourishes life rather than what drains you."},
        "blocked_expression": {"ru": "Забота превращается в навязчивость или творческий застой, когда нет отдачи.", "en": "Care turns into intrusiveness or creative stagnation when there is no reciprocation."},
    },
    4: {
        "inner_state": {"ru": "Ты чувствуешь потребность в порядке и защите, но тебе не хватает гибкости.", "en": "You feel a need for order and protection, but you lack flexibility."},
        "decision": {"ru": "Выбирай то, что создаёт устойчивую структуру, а не то, что ограничивает движение.", "en": "Choose what builds stable structure rather than what restricts movement."},
        "blocked_expression": {"ru": "Стремление к контролю превращается в жёсткость и подавление, когда нет доверия к другим.", "en": "The drive for control turns into rigidity and suppression when there is no trust in others."},
    },
    5: {
        "inner_state": {"ru": "Ты чувствуешь поиск смысла и принадлежности, но тебе не хватает личной правды.", "en": "You feel a search for meaning and belonging, but you lack personal truth."},
        "decision": {"ru": "Выбирай то, что соединяет с традицией, а не то, что отрывает от своих корней.", "en": "Choose what connects you to tradition rather than what cuts you from your roots."},
        "blocked_expression": {"ru": "Потребность в учении превращается в догматизм или зависимость от авторитета.", "en": "The need for teaching turns into dogmatism or dependence on authority."},
    },
    6: {
        "inner_state": {"ru": "Ты чувствуешь влечение и необходимость выбора, но тебе не хватает ясности в ценностях.", "en": "You feel attraction and the necessity of choice, but you lack clarity in your values."},
        "decision": {"ru": "Выбирай то, что соответствует твоим глубинным ценностям, а не то, что просто манит.", "en": "Choose what aligns with your deep values rather than what merely tempts."},
        "blocked_expression": {"ru": "Стремление к союзу превращается в нерешительность или слияние с чужим мнением.", "en": "The longing for union turns into indecision or merging with someone else's opinion."},
    },
    7: {
        "inner_state": {"ru": "Ты чувствуешь решимость и движение вперёд, но тебе не хватает согласованности частей себя.", "en": "You feel determination and forward movement, but you lack harmony between parts of yourself."},
        "decision": {"ru": "Выбирай то, что поддерживает твой курс, а не то, что рассеивает силы.", "en": "Choose what supports your course rather than what scatters your energy."},
        "blocked_expression": {"ru": "Воля к победе превращается в агрессию или бездумный напор, когда нет внутреннего равновесия.", "en": "The will to win turns into aggression or mindless drive when there is no inner balance."},
    },
    8: {
        "inner_state": {"ru": "Ты чувствуешь внутреннюю мягкость и одновременно стойкость, но тебе не хватает терпения к себе.", "en": "You feel inner gentleness and resilience at once, but you lack patience with yourself."},
        "decision": {"ru": "Выбирай то, что требует мягкой настойчивости, а не то, что давит.", "en": "Choose what requires gentle persistence rather than what applies force."},
        "blocked_expression": {"ru": "Сила превращается в подавление инстинктов или самобичевание, когда нет принятия своей природы.", "en": "Strength turns into suppression of instincts or self-flagellation when there is no acceptance of your nature."},
    },
    9: {
        "inner_state": {"ru": "Тебе нужно побыть одному, чтобы расслышать себя, а не чтобы спрятаться.", "en": "You need solitude to hear yourself, not to hide from everyone else."},
        "decision": {"ru": "Выбирай то, что оставляет место для паузы, а не то, что требует ответа прямо сейчас.", "en": "Choose the option that leaves room for a pause instead of demanding an answer right now."},
        "blocked_expression": {"ru": "Потребность в тишине превращается в отказ от разговоров, которых ты на самом деле ждёшь.", "en": "The need for quiet turns into refusing the very conversations you are waiting for."},
    },
    10: {
        "inner_state": {"ru": "Ты чувствуешь перемены и вращение обстоятельств, но тебе не хватает внутренней точки опоры.", "en": "You feel changes and the turning of circumstances, but you lack an inner anchor."},
        "decision": {"ru": "Выбирай то, что оставляет пространство для неожиданного, а не то, что пытается всё зафиксировать.", "en": "Choose what leaves room for the unexpected rather than what tries to freeze everything."},
        "blocked_expression": {"ru": "Принятие перемен превращается в фатализм или пассивное ожидание, когда нет участия.", "en": "Acceptance of change turns into fatalism or passive waiting when there is no participation."},
    },
    11: {
        "inner_state": {"ru": "Ты чувствуешь потребность в честности и равновесии, но тебе не хватает сострадания к себе.", "en": "You feel a need for honesty and equilibrium, but you lack compassion for yourself."},
        "decision": {"ru": "Выбирай то, что опирается на факты и справедливость, а не то, что выгодно лишь одной стороне.", "en": "Choose what is based on facts and fairness rather than what benefits only one side."},
        "blocked_expression": {"ru": "Стремление к правде превращается в холодную критику или самоосуждение.", "en": "The pursuit of truth turns into cold criticism or self-condemnation."},
    },
    12: {
        "inner_state": {"ru": "Ты чувствуешь паузу и смену перспективы, но тебе не хватает готовности отпустить.", "en": "You feel a pause and a shift of perspective, but you lack the willingness to let go."},
        "decision": {"ru": "Выбирай то, что позволяет увидеть ситуацию иначе, а не то, что держит в подвешенном состоянии.", "en": "Choose what allows you to see the situation differently rather than what keeps you suspended."},
        "blocked_expression": {"ru": "Готовность к жертве превращается в мученичество или застревание в ожидании.", "en": "Willingness to sacrifice turns into martyrdom or getting stuck in waiting."},
    },
    13: {
        "inner_state": {"ru": "Ты чувствуешь, что что-то завершается, и это освобождает, но тебе не хватает прощания.", "en": "You feel something ending, and it liberates, but you lack closure."},
        "decision": {"ru": "Выбирай то, что позволяет закрыть старую главу, а не то, что цепляется за уходящее.", "en": "Choose what allows you to close an old chapter rather than what clings to what is leaving."},
        "blocked_expression": {"ru": "Необходимость завершения превращается в застой или страх перемен, когда не даёшь себе отпустить.", "en": "The need for closure turns into stagnation or fear of change when you do not allow yourself to let go."},
    },
    14: {
        "inner_state": {"ru": "Ты чувствуешь потребность в гармонии и умеренности, но тебе не хватает синтеза противоположностей.", "en": "You feel a need for harmony and moderation, but you lack synthesis of opposites."},
        "decision": {"ru": "Выбирай то, что соединяет разные стороны, а не то, что требует крайностей.", "en": "Choose what bridges different sides rather than what demands extremes."},
        "blocked_expression": {"ru": "Стремление к балансу превращается в компромисс без души или прокрастинацию.", "en": "The pursuit of balance turns into soulless compromise or procrastination."},
    },
    15: {
        "inner_state": {"ru": "Ты чувствуешь привязанность к чему-то, что тебя ограничивает, но тебе не хватает осознания выбора.", "en": "You feel attachment to something that limits you, but you lack awareness of choice."},
        "decision": {"ru": "Выбирай то, что не держит тебя на крючке, а не то, что даёт временное удовольствие.", "en": "Choose what does not keep you hooked rather than what gives temporary pleasure."},
        "blocked_expression": {"ru": "Страсть превращается в одержимость или саморазрушение, когда нет границ.", "en": "Passion turns into obsession or self-destruction when there are no boundaries."},
    },
    16: {
        "inner_state": {"ru": "Ты чувствуешь, как рушится то, что казалось незыблемым, и это освобождает, но пугает.", "en": "You feel what seemed unshakable crumbling, and it liberates but frightens."},
        "decision": {"ru": "Выбирай то, что строится на честном основании, а не то, что держится на иллюзиях.", "en": "Choose what is built on an honest foundation rather than what stands on illusions."},
        "blocked_expression": {"ru": "Потребность в разрушении старого превращается в саморазрушение или хаос, если не дать выход.", "en": "The need to tear down the old turns into self-destruction or chaos if not given an outlet."},
    },
    17: {
        "inner_state": {"ru": "Ты чувствуешь надежду и обновление, но тебе не хватает доверия к будущему.", "en": "You feel hope and renewal, but you lack trust in the future."},
        "decision": {"ru": "Выбирай то, что вдохновляет и лечит, а не то, что отнимает веру.", "en": "Choose what inspires and heals rather than what takes away faith."},
        "blocked_expression": {"ru": "Надежда превращается в наивность или пассивное ожидание чуда, когда нет действия.", "en": "Hope turns into naivety or passive waiting for a miracle when there is no action."},
    },
    18: {
        "inner_state": {"ru": "Ты чувствуешь неопределённость и влияние подсознания, но тебе не хватает ясности.", "en": "You feel uncertainty and the influence of the subconscious, but you lack clarity."},
        "decision": {"ru": "Выбирай то, что оставляет место для неизвестного, а не то, что требует полного света.", "en": "Choose what leaves room for the unknown rather than what demands full light."},
        "blocked_expression": {"ru": "Интуиция превращается в тревогу или бегство в иллюзии, когда нет опоры.", "en": "Intuition turns into anxiety or escape into illusions when there is no grounding."},
    },
    19: {
        "inner_state": {"ru": "Ты чувствуешь радость и ясность, но тебе не хватает принятия своей уязвимости.", "en": "You feel joy and clarity, but you lack acceptance of your vulnerability."},
        "decision": {"ru": "Выбирай то, что приносит тепло и открытость, а не то, что скрывает от света.", "en": "Choose what brings warmth and openness rather than what hides from the light."},
        "blocked_expression": {"ru": "Жизнерадостность превращается в поверхностность или отрицание проблем.", "en": "Cheerfulness turns into superficiality or denial of problems."},
    },
    20: {
        "inner_state": {"ru": "Ты чувствуешь пробуждение и призыв к переменам, но тебе не хватает прощения себя.", "en": "You feel awakening and a call to change, but you lack self-forgiveness."},
        "decision": {"ru": "Выбирай то, что даёт второй шанс, а не то, что держит в прошлом.", "en": "Choose what gives a second chance rather than what keeps you in the past."},
        "blocked_expression": {"ru": "Потребность в обновлении превращается в самокритику или страх осуждения.", "en": "The need for renewal turns into self-criticism or fear of judgment."},
    },
    21: {
        "inner_state": {"ru": "Ты чувствуешь завершённость и целостность, но тебе не хватает нового вызова.", "en": "You feel completion and wholeness, but you lack a new challenge."},
        "decision": {"ru": "Выбирай то, что интегрирует опыт, а не то, что начинает всё с нуля.", "en": "Choose what integrates experience rather than what starts over from scratch."},
        "blocked_expression": {"ru": "Чувство завершённости превращается в застой или нежелание выходить за пределы.", "en": "The feeling of completion turns into stagnation or unwillingness to step beyond."},
    },
}
