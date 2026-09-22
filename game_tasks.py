"""Pure route and task generation for MathCraft."""

import random

from game_content import (
    LOGIC_TASKS,
    MOB_POOLS,
    PLAYER_PROFILES,
    ROUTE_TEMPLATES,
    STEPS_PER_WORLD,
    TOTAL_QUESTS,
    WORLDS,
)


def create_marathon_route(profile_name):
    difficulty = PLAYER_PROFILES.get(profile_name, PLAYER_PROFILES["Ксения"])["difficulty"]
    route = []
    for world_idx, operation_variants in enumerate(ROUTE_TEMPLATES[difficulty]):
        mob_id, mob_name = random.choice(MOB_POOLS[world_idx])
        route.append({
            "ops": list(random.choice(operation_variants)),
            "mob_id": mob_id,
            "mob_name": mob_name,
            "mob_step": random.randint(3, 8),
        })
    return route


def create_treasure_tasks():
    return [world_idx * STEPS_PER_WORLD + random.randint(1, STEPS_PER_WORLD) for world_idx in range(len(WORLDS))]


def create_sage_task(route, start_at=1):
    occupied = {
        world_idx * STEPS_PER_WORLD + world.get("mob_step", 5)
        for world_idx, world in enumerate(route)
    }
    candidates = [
        task for task in range(max(2, start_at), TOTAL_QUESTS)
        if task % STEPS_PER_WORLD != 0 and task not in occupied
    ]
    return random.choice(candidates) if candidates else None


def create_adaptive_tasks(profile, count=3):
    """Replace a few future tasks with the player's most troublesome errors."""
    history_details = []
    for game in profile.get("game_history", []):
        history_details.extend(game.get("error_details", []))

    current_details = profile.get("marathon_error_details", [])
    last_game_details = (
        profile.get("game_history", [])[-1].get("error_details", [])
        if profile.get("game_history") else []
    )
    if current_details != last_game_details:
        history_details.extend(current_details)

    ranked = {}
    for order, detail in enumerate(history_details):
        expression = detail.get("expr")
        answer = detail.get("correct")
        if not expression or not isinstance(answer, int):
            continue
        key = (expression, answer)
        if key not in ranked:
            ranked[key] = {"count": 0, "last_seen": order, "detail": detail}
        ranked[key]["count"] += 1
        ranked[key]["last_seen"] = order
        ranked[key]["detail"] = detail

    difficult = sorted(
        ranked.values(),
        key=lambda item: (item["count"], item["last_seen"]),
        reverse=True,
    )[:count]
    if not difficult:
        return {}

    selected_worlds = random.sample(range(len(WORLDS)), len(difficult))
    task_numbers = [
        world_idx * STEPS_PER_WORLD + random.randint(1, STEPS_PER_WORLD)
        for world_idx in selected_worlds
    ]
    adaptive = {}
    for task_number, item in zip(task_numbers, difficult):
        detail = item["detail"]
        adaptive[str(task_number)] = {
            "expr": detail["expr"],
            "correct": detail["correct"],
            "wrong": detail.get("wrong"),
        }
    return adaptive


def get_route_world(profile, world_idx):
    route = profile.get("marathon_route", []) if profile else []
    if 0 <= world_idx < len(route):
        return route[world_idx]
    return {
        "ops": WORLDS[world_idx]["ops"],
        "mob_id": WORLDS[world_idx]["mob_id"],
        "mob_name": WORLDS[world_idx]["mob_name"],
    }


def make_answer_choices(answer, minimum, maximum):
    """Build three unique nearby answers, including the correct one."""
    variants = {answer}
    offsets = [-3, -2, -1, 1, 2, 3]
    random.shuffle(offsets)
    for offset in offsets:
        candidate = answer + offset
        if minimum <= candidate <= maximum:
            variants.add(candidate)
        if len(variants) == 3:
            break
    if len(variants) < 3:
        for candidate in range(minimum, maximum + 1):
            variants.add(candidate)
            if len(variants) == 3:
                break
    choices = list(variants)
    random.shuffle(choices)
    return choices


def make_math_task(ops_list, profile_name, force_missing=False):
    op = random.choice(ops_list)
    is_hard = PLAYER_PROFILES.get(profile_name, {}).get("difficulty") == "hard"
    max_answer = 100 if is_hard else 20

    if op == "+":
        ans = random.randint(20, max_answer) if is_hard else random.randint(5, max_answer)
        a = random.randint(5 if is_hard else 2, ans - (5 if is_hard else 2))
        b = ans - a
        sym = "+"
    elif op == "-":
        a = random.randint(20, max_answer) if is_hard else random.randint(6, max_answer)
        b = random.randint(5 if is_hard else 2, a - (5 if is_hard else 2))
        ans = a - b
        sym = "-"
    elif op == "*":
        pairs = [
            (x, y)
            for x in range(2, 11)
            for y in range(2, 11)
            if is_hard or x * y <= 20
        ]
        a, b = random.choice(pairs)
        ans = a * b
        sym = "x"
    else:
        div_pairs = []
        for divisor in range(2, 11):
            max_result = 10 if is_hard else (20 // divisor)
            for result in range(2, max_result + 1):
                div_pairs.append((divisor * result, divisor, result))
        a, b, ans = random.choice(div_pairs)
        sym = ":"

    if force_missing or random.random() < 0.25:
        hide_left = random.choice([True, False])
        missing_answer = a if hide_left else b
        missing_min = 2
        if op in ("*", "/") and not (op == "/" and hide_left):
            missing_max = 10
        else:
            missing_max = max_answer
        left = "?" if hide_left else str(a)
        right = str(b) if hide_left else "?"
        equation = f"{left} {sym} {right} = {ans}"
        return (
            equation,
            missing_answer,
            make_answer_choices(missing_answer, missing_min, missing_max),
            op,
            equation,
        )

    return (
        f"{a} {sym} {b} = ?",
        ans,
        make_answer_choices(ans, 1, max_answer),
        op,
        f"{a} {sym} {b}",
    )


def make_review_task(error_detail):
    answer = error_detail["correct"]
    variants = {answer}
    wrong_answer = error_detail.get("wrong")
    if isinstance(wrong_answer, int) and wrong_answer != answer:
        variants.add(wrong_answer)
    while len(variants) < 3:
        candidate = answer + random.choice([-3, -2, -1, 1, 2, 3])
        if candidate >= 0:
            variants.add(candidate)
    choices = list(variants)
    random.shuffle(choices)
    expression = error_detail["expr"]
    question = expression if "?" in expression else f"{expression} = ?"
    return question, answer, choices, "review", expression


def pick_logic_task(profile_name, previous_question=None):
    difficulty = PLAYER_PROFILES.get(profile_name, PLAYER_PROFILES["Ксения"])["difficulty"]
    available = [task for task in LOGIC_TASKS[difficulty] if task["question"] != previous_question]
    task = random.choice(available or LOGIC_TASKS[difficulty])
    choices = list(task["choices"])
    random.shuffle(choices)
    return task["question"], task["answer"], choices
