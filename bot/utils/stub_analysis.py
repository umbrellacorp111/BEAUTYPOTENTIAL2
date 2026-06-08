import random
from datetime import datetime

GROWTH_ZONES = [
    "Причёска и укладка",
    "Форма бровей",
    "Цветовая гамма гардероба",
    "Осанка и положение корпуса",
    "Состояние кожи лица",
    "Стиль очков / аксессуаров",
    "Форма одежды по типу фигуры",
    "Макияж (естественные техники)",
    "Цвет волос под тон кожи",
    "Линия роста бороды / усов",
]

MISTAKES = [
    "Одежда не по фигуре — скрывает достоинства",
    "Неподходящий цвет волос под тон кожи",
    "Отсутствие акцента на сильных чертах лица",
    "Гардероб в одной цветовой гамме без контрастов",
    "Пренебрежение причёской как инструментом коррекции лица",
    "Неправильная форма очков для типа лица",
    "Слишком тёмные/светлые тона в одежде",
    "Отсутствие вертикальных линий в образе",
    "Неучтённые пропорции верхней и нижней части тела",
    "Пренебрежение аксессуарами (шейные платки, серьги)",
]

STRENGTHS = [
    "Правильные пропорции лица",
    "Хорошая симметрия черт",
    "Выразительные глаза",
    "Чёткая линия скул",
    "Правильный овал лица",
    "Хорошая осанка",
    "Удачное соотношение плеч и бёдер",
    "Чистая кожа без явных проблем",
    "Выразительная линия губ",
    "Природный оттенок волос",
]

DETAILED_TIPS = [
    "Заменить базовый гардероб на 3-4 вещи нейтральных оттенков",
    "Сменить форму стрижки на более объёмную в верхней части",
    "Добавить один акцентный аксессуар (платок, часы, серьги)",
    "Скорректировать линию бровей — это меняет выражение лица на 30%",
    "Носить вещи с вертикальными линиями — визуально стройнит",
    "Выбирать верх с V-образным вырезом",
    "Добавить в гардероб один яркий предмет как accent piece",
    "Сменить цвет волос на тон теплее/холоднее",
]

STEP_BY_STEP = [
    "Шаг 1. Скорректировать причёску (запись к барберу/стилисту)",
    "Шаг 2. Обновить базовый гардероб: 3 вещи нейтральных цветов",
    "Шаг 3. Добавить 1 акцентный аксессуар",
    "Шаг 4. Работа над осанкой (10 мин/день упражнений)",
    "Шаг 5. Сменить цвет волос на +1 тон к натуральному",
    "Шаг 6. Подобрать форму очков под тип лица",
    "Шаг 7. Обновить форму бровей",
    "Шаг 8. Ввести правило одного яркого акцента в образе",
]

RECOMMENDED_PRODUCTS = [
    "Матрица сочетаемости цветов в одежде",
    "Чек-лист «10 минут на утро» для внешности",
    "Гайд по выбору стрижки под форму лица",
    "Гайд по цветотипу: тёплая / холодная палитра",
]


def generate_free_analysis(age: int, goals: list[str]) -> dict:
    random.seed(datetime.now().timestamp())
    current_potential = random.randint(43, 68)
    growth_zone = random.choice(GROWTH_ZONES)
    if goals:
        for g in goals:
            if g == "Лицо / черты":
                growth_zone = random.choice(["Форма бровей", "Состояние кожи лица"])
                break
            elif g == "Стиль одежды":
                growth_zone = random.choice(["Цветовая гамма гардероба", "Форма одежды по типу фигуры"])
                break
            elif g == "Причёска":
                growth_zone = random.choice(["Причёска и укладка", "Цвет волос под тон кожи"])
                break

    mistake = random.choice(MISTAKES)
    potential_after = current_potential + random.randint(13, 28)
    potential_after = min(potential_after, 93)

    return {
        "current_potential": current_potential,
        "growth_zone": growth_zone,
        "mistake": mistake,
        "potential_after": potential_after,
    }


def generate_full_report(age: int, goals: list[str]) -> str:
    random.seed(datetime.now().timestamp() + 1000)
    free = generate_free_analysis(age, goals)
    strengths = random.sample(STRENGTHS, 3)
    tips = random.sample(DETAILED_TIPS, 4)
    steps = random.sample(STEP_BY_STEP, 5)
    products = random.sample(RECOMMENDED_PRODUCTS, 2)

    lines = [
        f"📊 ТЕКУЩИЙ ПОТЕНЦИАЛ: {free['current_potential']}%",
        "",
        "✅ СИЛЬНЫЕ СТОРОНЫ:",
    ]
    for s in strengths:
        lines.append(f"  • {s}")

    lines.extend([
        "",
        f"❌ ГЛАВНАЯ ОШИБКА:",
        f"  {free['mistake']}",
        "",
        f"🎯 ТРИ ТОЧКИ РОСТА (80% РЕЗУЛЬТАТА):",
    ])
    for i, tip in enumerate(tips[:3], 1):
        lines.append(f"  {i}. {tip}")

    lines.extend([
        "",
        f"📈 ПРОГНОЗ ПОСЛЕ ИЗМЕНЕНИЙ: {free['potential_after']}%",
        "",
        "📋 ПЛАН ДЕЙСТВИЙ (ПОШАГОВО):",
    ])
    for step in steps:
        lines.append(f"  {step}")

    lines.extend([
        "",
        "📌 РЕКОМЕНДУЕМЫЕ МАТЕРИАЛЫ:",
    ])
    for p in products:
        lines.append(f"  • {p}")

    return "\n".join(lines)
