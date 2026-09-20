import pygame
import random
import sys
import math
import json
import os
import asyncio
from array import array
from datetime import date, datetime

# Инициализация
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 1000, 600

if "ANDROID_ARGUMENT" in os.environ:
    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.FULLSCREEN | pygame.SCALED
    )
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Майнкрафт: Марафон 50")
clock = pygame.time.Clock()

FONT_SCALE = 1.35

def get_safe_font(size):
    """Create a UI font enlarged for high-density phone screens."""
    return pygame.font.Font(None, round(size * FONT_SCALE))

FONT_TITLE = get_safe_font(28)
FONT_BIG = get_safe_font(22)
FONT_MED = get_safe_font(18)
FONT_SMALL = get_safe_font(15)
FONT_TINY = get_safe_font(12)

sound_enabled = True
audio_attempted = False
game_sounds = {}

def ensure_audio():
    """Initialize audio after a user gesture (required by browsers and Android)."""
    global audio_attempted, game_sounds
    if audio_attempted:
        return
    audio_attempted = True
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

        sample_rate, sample_format, channels = pygame.mixer.get_init()
        if sample_format != -16:
            return

        def make_tone(frequency, duration_ms, volume=0.18):
            sample_count = int(sample_rate * duration_ms / 1000)
            fade_samples = max(1, int(sample_rate * 0.015))
            samples = array("h")
            for i in range(sample_count):
                fade_in = min(1.0, i / fade_samples)
                fade_out = min(1.0, (sample_count - i) / fade_samples)
                envelope = min(fade_in, fade_out)
                value = int(32767 * volume * envelope * math.sin(2 * math.pi * frequency * i / sample_rate))
                for _ in range(channels):
                    samples.append(value)
            return pygame.mixer.Sound(buffer=samples.tobytes())

        game_sounds = {
            "correct": make_tone(660, 110),
            "wrong": make_tone(180, 180),
            "hit": make_tone(440, 90, 0.22),
            "purchase": make_tone(880, 140),
            "victory": make_tone(990, 320, 0.22),
        }
    except (pygame.error, ValueError):
        game_sounds = {}

def play_sound(name):
    if sound_enabled:
        ensure_audio()
        sound = game_sounds.get(name)
        if sound:
            sound.play()

# Палитра Minecraft
MC_GUI_BG = (198, 198, 198)
MC_GUI_LIGHT = (255, 255, 255)
MC_GUI_DARK = (85, 85, 85)
MC_GUI_BLACK = (0, 0, 0)
MC_SLOT_BG = (139, 139, 139)
MC_EMERALD = (0, 215, 75)
MC_EMERALD_DARK = (0, 140, 50)
MC_GOLD = (255, 215, 0)
GOLD = MC_GOLD

DARK_TEXT = (45, 45, 45)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (35, 175, 60)
PURPLE = (180, 50, 240)

WORLDS = [
    {"name": "1. Равнины Обычного Мира", "sky": (140, 205, 255), "ground": (85, 140, 50), "plat": (115, 80, 50), "top_plat": (105, 175, 55), "dark_text": True, "ops": ["+", "-"], "vehicle_type": "pig", "v_name": "Свинка", "upg_name": "Бронированная свинка", "upg_cost": 70, "mob_id": "creeper", "mob_name": "Крипер"},
    {"name": "2. Жаркая Пустыня", "sky": (245, 215, 160), "ground": (210, 165, 85), "plat": (180, 130, 60), "top_plat": (225, 185, 100), "dark_text": True, "ops": ["-", "+"], "vehicle_type": "llama", "v_name": "Лама", "upg_name": "Боевая Лама в попоне", "upg_cost": 110, "mob_id": "skeleton", "mob_name": "Скелет с луком"},
    {"name": "3. Ледяные Равнины", "sky": (195, 225, 245), "ground": (220, 235, 245), "plat": (140, 190, 230), "top_plat": (175, 220, 255), "dark_text": True, "ops": ["*"], "vehicle_type": "boat", "v_name": "Лодка на льду", "upg_name": "Лодка с сундуком", "upg_cost": 160, "mob_id": "stray", "mob_name": "Зимогор"},
    {"name": "4. Незер (Нижний Мир)", "sky": (65, 15, 15), "ground": (90, 20, 20), "plat": (50, 10, 10), "top_plat": (240, 90, 20), "dark_text": False, "ops": ["/"], "vehicle_type": "strider", "v_name": "Страйдер по лаве", "upg_name": "Страйдер в седле", "upg_cost": 220, "mob_id": "blaze", "mob_name": "Ифрит Незера"},
    {"name": "5. Эндер Мир (Край)", "sky": (15, 10, 25), "ground": (30, 25, 45), "plat": (50, 45, 70), "top_plat": (230, 230, 175), "dark_text": False, "ops": ["+", "-", "*", "/"], "vehicle_type": "dragon", "v_name": "Элитры", "upg_name": "Дракон Края", "upg_cost": 300, "mob_id": "enderman", "mob_name": "Эндермен"}
]

HELMETS = {
    "none": {"name": "Без шлема", "cost": 0, "max_durability": 0, "repair_cost": 0},
    "leather": {"name": "Кожаный шлем", "cost": 50, "color": (160, 90, 45), "max_durability": 3, "repair_cost": 20},
    "iron": {"name": "Железный шлем", "cost": 100, "color": (210, 210, 215), "max_durability": 6, "repair_cost": 40},
    "diamond": {"name": "Алмазный шлем", "cost": 180, "color": (45, 225, 220), "max_durability": 10, "repair_cost": 75},
    "netherite": {"name": "Незеритовый шлем", "cost": 300, "color": (65, 55, 65), "max_durability": 16, "repair_cost": 120}
}

ARTIFACTS = {
    "sharp_sword": {"name": "Меч «Острота»", "desc": "Мобы биомов: нужно всего 2 примера!", "cost": 150},
    "strength_potion": {"name": "Зелье Силы II", "desc": "Мобы биомов: победа с 1 примера (ваншот)!", "cost": 250},
    "dragon_bow": {"name": "Лук Силы", "desc": "Дракон Края: нужно 4 примера (вместо 5)!", "cost": 220},
    "end_crystal": {"name": "Кристалл Края", "desc": "Дракон Края: нужно всего 3 примера!", "cost": 350}
}

POTIONS = {
    "totem": {"name": "Тотем Бессмертия", "desc": "Спасает от 1 ошибки в бою со стражем или Драконом!", "cost": 75, "max": 3},
    "luck": {"name": "Зелье Удачи", "desc": "Даёт удвоенные изумруды на следующие 10 примеров!", "cost": 100, "max": 1}
}

PLAYER_PROFILES = {
    "Ксения": {"grade": 3, "difficulty": "easy"},
    "Настя": {"grade": 5, "difficulty": "hard"},
}

LOGIC_TASKS = {
    "easy": [
        {"question": "Продолжи ряд: 2, 4, 6, 8, ?", "choices": [9, 10, 12], "answer": 10},
        {"question": "У трёх кошек по 2 уха. Сколько ушей?", "choices": [5, 6, 8], "answer": 6},
        {"question": "Сегодня среда. Какой день будет через 2 дня?", "choices": ["Пятница", "Суббота", "Вторник"], "answer": "Пятница"},
        {"question": "Что тяжелее: 1 кг железа или 1 кг ваты?", "choices": ["Железо", "Одинаково", "Вата"], "answer": "Одинаково"},
        {"question": "Продолжи: круг, квадрат, круг, квадрат, ...", "choices": ["Круг", "Треугольник", "Квадрат"], "answer": "Круг"},
        {"question": "В комнате 4 угла. В каждом углу кот. Сколько котов?", "choices": [4, 8, 16], "answer": 4},
    ],
    "hard": [
        {"question": "Продолжи ряд: 3, 6, 12, 24, ?", "choices": [36, 42, 48], "answer": 48},
        {"question": "Два отца и два сына нашли 3 ключа — по одному каждому. Сколько их?", "choices": [3, 4, 6], "answer": 3},
        {"question": "Все драконы летают. Гоша — дракон. Что верно?", "choices": ["Гоша летает", "Гоша плавает", "Неизвестно"], "answer": "Гоша летает"},
        {"question": "Какое число лишнее: 2, 4, 7, 8, 10?", "choices": [2, 7, 10], "answer": 7},
        {"question": "У Ани больше монет, чем у Веры, а у Веры больше, чем у Лены. У кого меньше?", "choices": ["У Ани", "У Веры", "У Лены"], "answer": "У Лены"},
        {"question": "Продолжи ряд: 1, 4, 9, 16, ?", "choices": [20, 25, 32], "answer": 25},
    ],
}

MOB_POOLS = [
    [("creeper", "Крипер"), ("zombie", "Зомби"), ("spider", "Паук")],
    [("skeleton", "Скелет"), ("husk", "Кадавр"), ("cave_spider", "Пещерный паук")],
    [("stray", "Зимогор"), ("witch", "Ведьма"), ("snow_golem", "Снежный голем")],
    [("blaze", "Ифрит"), ("magma_cube", "Магмовый куб"), ("piglin", "Пиглин")],
    [("enderman", "Эндермен"), ("shulker", "Шалкер"), ("endermite", "Эндермит")],
]

ROUTE_TEMPLATES = {
    "easy": [
        [["+"], ["-"], ["+", "-"]],
        [["+", "-"], ["+"], ["-"]],
        [["*"], ["*", "+"]],
        [["/"], ["*", "/"]],
        [["+", "-", "*", "/"], ["+", "-", "*"]],
    ],
    "hard": [
        [["+", "-"], ["+"], ["-"]],
        [["+", "-", "*"], ["+", "*"]],
        [["*", "/"], ["*", "+", "-"]],
        [["/", "*", "-"], ["/", "+"]],
        [["+", "-", "*", "/"], ["*", "/", "+"]],
    ],
}

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
    return [world_idx * 10 + random.randint(1, 10) for world_idx in range(5)]

def create_sage_task(route, start_at=1):
    occupied = {
        world_idx * 10 + world.get("mob_step", 5)
        for world_idx, world in enumerate(route)
    }
    candidates = [
        task for task in range(max(2, start_at), TOTAL_QUESTS)
        if task % STEPS_PER_WORLD != 0 and task not in occupied
    ]
    return random.choice(candidates) if candidates else None

def get_route_world(profile, world_idx):
    route = profile.get("marathon_route", []) if profile else []
    if 0 <= world_idx < len(route):
        return route[world_idx]
    return {
        "ops": WORLDS[world_idx]["ops"],
        "mob_id": WORLDS[world_idx]["mob_id"],
        "mob_name": WORLDS[world_idx]["mob_name"],
    }

SAVE_FILE = "mc_math_save.json"
LAST_PLAYER_FILE = "mc_last_player.txt"

def request_browser_fullscreen():
    if sys.platform == "emscripten":
        try:
            import platform
            doc = platform.window.document
            if not doc.fullscreenElement:
                doc.documentElement.requestFullscreen()
        except Exception:
            pass

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def get_last_player():
    if os.path.exists(LAST_PLAYER_FILE):
        try:
            with open(LAST_PLAYER_FILE, "r", encoding="utf-8") as f:
                n = f.read().strip()
                if n: return n
        except Exception:
            return None
    return None

def set_last_player(name):
    try:
        with open(LAST_PLAYER_FILE, "w", encoding="utf-8") as f:
            f.write(name.strip())
    except Exception:
        pass

def get_player(name, apply_daily_bonus=True):
    profiles = load_data()
    name = name.strip()
    today_str = date.today().isoformat()
    if name not in profiles:
        new_route = create_marathon_route(name)
        profiles[name] = {
            "emeralds": 10, "streak": 1, "last_date": today_str,
            "task_num": 1, "helmet": "none", "unlocked_helmets": ["none"],
            "upgraded_vehicles": [], "artifacts": [], "totems": 1, "luck_timer": 0,
            "marathon_errors": 0, "marathon_error_details": [], "sound_enabled": True,
            "game_history": [], "boss_penalty_errors": 0, "helmet_protections": 0,
            "helmet_durability": {"none": 0},
            "marathon_route": new_route,
            "treasure_tasks": create_treasure_tasks(),
            "sage_task": create_sage_task(new_route),
            "sage_completed": False,
            "sage_artifact": None,
        }
    else:
        p = profiles[name]
        if apply_daily_bonus:
            last_d = datetime.fromisoformat(p.get("last_date", today_str)).date()
            diff = (date.today() - last_d).days
            if diff == 1:
                p["streak"] += 1
                p["emeralds"] += 5
                p["last_date"] = today_str
            elif diff > 1:
                p["streak"] = 1
                p["last_date"] = today_str
        if "task_num" not in p: p["task_num"] = 1
        if "upgraded_vehicles" not in p: p["upgraded_vehicles"] = []
        if "artifacts" not in p: p["artifacts"] = []
        if "totems" not in p: p["totems"] = 1
        if "luck_timer" not in p: p["luck_timer"] = 0
        if "marathon_errors" not in p: p["marathon_errors"] = 0
        if "marathon_error_details" not in p: p["marathon_error_details"] = []
        if "sound_enabled" not in p: p["sound_enabled"] = True
        if "game_history" not in p: p["game_history"] = []
        if "boss_penalty_errors" not in p: p["boss_penalty_errors"] = p.get("marathon_errors", 0)
        if "helmet_protections" not in p: p["helmet_protections"] = 0
        if "helmet_durability" not in p: p["helmet_durability"] = {"none": 0}
        if len(p.get("marathon_route", [])) != len(WORLDS):
            p["marathon_route"] = create_marathon_route(name)
        for world in p["marathon_route"]:
            if "mob_step" not in world:
                world["mob_step"] = random.randint(3, 8)
        if len(p.get("treasure_tasks", [])) != len(WORLDS):
            p["treasure_tasks"] = create_treasure_tasks()
        if "sage_task" not in p:
            p["sage_task"] = create_sage_task(p["marathon_route"], p.get("task_num", 1))
        if "sage_completed" not in p: p["sage_completed"] = False
        if "sage_artifact" not in p: p["sage_artifact"] = None
        for helmet_id in p.get("unlocked_helmets", ["none"]):
            if helmet_id != "none" and helmet_id not in p["helmet_durability"]:
                p["helmet_durability"][helmet_id] = HELMETS.get(helmet_id, {}).get("max_durability", 0)
        equipped_helmet = p.get("helmet", "none")
        if equipped_helmet != "none" and p["helmet_durability"].get(equipped_helmet, 0) <= 0:
            p["helmet"] = "none"

    save_data(profiles)
    set_last_player(name)
    return profiles[name]

def use_helmet_protection(profile):
    """Consume one durability point and shield the boss-health penalty."""
    helmet_id = profile.get("helmet", "none")
    helmet_info = HELMETS.get(helmet_id, HELMETS["none"])
    if helmet_id == "none" or helmet_info.get("max_durability", 0) <= 0:
        return None

    durability = profile.setdefault("helmet_durability", {})
    remaining = durability.get(helmet_id, helmet_info["max_durability"])
    if remaining <= 0:
        profile["helmet"] = "none"
        return None

    remaining -= 1
    durability[helmet_id] = remaining
    profile["helmet_protections"] = profile.get("helmet_protections", 0) + 1
    broken = remaining == 0
    if broken:
        profile["helmet"] = "none"

    return {
        "helmet_id": helmet_id,
        "helmet_name": helmet_info["name"],
        "remaining": remaining,
        "maximum": helmet_info["max_durability"],
        "broken": broken,
    }

def make_math_task(ops_list):
    op = random.choice(ops_list)
    is_hard = PLAYER_PROFILES.get(globals().get("player_name"), {}).get("difficulty") == "hard"
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
        for d in range(2, 11):
            max_result = 10 if is_hard else (20 // d)
            for res in range(2, max_result + 1):
                div_pairs.append((d * res, d, res))
        a, b, ans = random.choice(div_pairs)
        sym = ":"

    variants = {ans}
    while len(variants) < 3:
        fake = ans + random.choice([-3, -2, -1, 1, 2, 3])
        if 1 <= fake <= max_answer and fake != ans:
            variants.add(fake)
            
    v_list = list(variants)
    random.shuffle(v_list)
    return f"{a} {sym} {b} = ?", ans, v_list, op, f"{a} {sym} {b}"

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
    return f"{expression} = ?", answer, choices, "review", expression

def pick_logic_task(profile_name, previous_question=None):
    difficulty = PLAYER_PROFILES.get(profile_name, PLAYER_PROFILES["Ксения"])["difficulty"]
    available = [task for task in LOGIC_TASKS[difficulty] if task["question"] != previous_question]
    task = random.choice(available or LOGIC_TASKS[difficulty])
    choices = list(task["choices"])
    random.shuffle(choices)
    return task["question"], task["answer"], choices

def draw_centered_wrapped_text(surf, text, font, color, center_x, top_y, max_width, line_gap=4):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    for line_idx, line in enumerate(lines):
        rendered = font.render(line, True, color)
        surf.blit(rendered, (center_x - rendered.get_width() // 2, top_y + line_idx * (font.get_height() + line_gap)))

def draw_mc_button(surf, rect, text, hovered=False, active=True, font_pref=None, custom_bg=None):
    if custom_bg:
        bg_color = (min(custom_bg[0] + 30, 255), min(custom_bg[1] + 30, 255), min(custom_bg[2] + 30, 255)) if hovered else custom_bg
    else:
        bg_color = (175, 175, 175) if (hovered and active) else (145, 145, 145) if active else (100, 100, 100)
    
    pygame.draw.rect(surf, bg_color, rect)
    pygame.draw.line(surf, MC_GUI_LIGHT, (rect.left, rect.top), (rect.right - 1, rect.top), 2)
    pygame.draw.line(surf, MC_GUI_LIGHT, (rect.left, rect.top), (rect.left, rect.bottom - 1), 2)
    pygame.draw.line(surf, MC_GUI_DARK, (rect.left, rect.bottom - 2), (rect.right - 1, rect.bottom - 2), 2)
    pygame.draw.line(surf, MC_GUI_DARK, (rect.right - 2, rect.top), (rect.right - 2, rect.bottom - 1), 2)
    pygame.draw.rect(surf, MC_GUI_BLACK, rect, 2)

    font = font_pref or FONT_MED
    txt_surf = font.render(text, True, (255, 255, 160) if (hovered and active) else WHITE)
    if txt_surf.get_width() > rect.width - 8:
        font = FONT_SMALL
        txt_surf = font.render(text, True, (255, 255, 160) if (hovered and active) else WHITE)
    if txt_surf.get_width() > rect.width - 8:
        font = FONT_TINY
        txt_surf = font.render(text, True, (255, 255, 160) if (hovered and active) else WHITE)

    shadow = font.render(text, True, (45, 45, 45))
    surf.blit(shadow, (rect.centerx - txt_surf.get_width() // 2 + 1, rect.centery - txt_surf.get_height() // 2 + 1))
    surf.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))

def draw_emerald(surf, cx, cy, r=9):
    pts = [(cx, cy - r), (cx + int(r*0.75), cy - int(r*0.4)), (cx + int(r*0.75), cy + int(r*0.4)),
           (cx, cy + r), (cx - int(r*0.75), cy + int(r*0.4)), (cx - int(r*0.75), cy - int(r*0.4))]
    pygame.draw.polygon(surf, MC_EMERALD, pts)
    pygame.draw.polygon(surf, MC_EMERALD_DARK, pts, 2)
    pygame.draw.circle(surf, (160, 255, 190), (cx - 2, cy - 2), 2)

def draw_mc_heart(surf, cx, cy, filled=True):
    if filled:
        pygame.draw.rect(surf, (220, 20, 20), (cx - 9, cy - 7, 8, 8))
        pygame.draw.rect(surf, (220, 20, 20), (cx + 1, cy - 7, 8, 8))
        pygame.draw.polygon(surf, (220, 20, 20), [(cx - 9, cy), (cx + 9, cy), (cx, cy + 9)])
        pygame.draw.rect(surf, WHITE, (cx - 7, cy - 5, 2, 2))
    else:
        pygame.draw.rect(surf, (60, 60, 60), (cx - 9, cy - 7, 18, 16))
    pygame.draw.rect(surf, MC_GUI_BLACK, (cx - 10, cy - 8, 20, 18), 1)

def draw_readable_badge(surf, center_x, center_y, text, border_col=(70, 70, 75), text_col=WHITE, font=None):
    use_font = font or FONT_MED
    t_surf = use_font.render(text, True, text_col)
    badge = pygame.Rect(
        center_x - t_surf.get_width() // 2 - 14,
        center_y - t_surf.get_height() // 2 - 5,
        t_surf.get_width() + 28,
        t_surf.get_height() + 10
    )
    pygame.draw.rect(surf, (28, 28, 32), badge, border_radius=6)
    pygame.draw.rect(surf, border_col, badge, 1, border_radius=6)
    surf.blit(t_surf, (center_x - t_surf.get_width() // 2, center_y - t_surf.get_height() // 2))

def draw_mc_slot_frame(surf, x, y, size=50):
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surf, MC_SLOT_BG, rect)
    pygame.draw.line(surf, (55, 55, 55), (rect.left, rect.top), (rect.right - 1, rect.top), 2)
    pygame.draw.line(surf, (55, 55, 55), (rect.left, rect.top), (rect.left, rect.bottom - 1), 2)
    pygame.draw.line(surf, WHITE, (rect.left, rect.bottom - 2), (rect.right - 1, rect.bottom - 2), 2)
    pygame.draw.line(surf, WHITE, (rect.right - 2, rect.top), (rect.right - 2, rect.bottom - 1), 2)
    return rect

def draw_item_icon(surf, item_type, cx, cy):
    if item_type.startswith("helm_"):
        h_code = item_type.replace("helm_", "")
        col_map = {"none": (120, 120, 120), "leather": (160, 90, 45), "iron": (215, 215, 220), "diamond": (45, 225, 220), "netherite": (65, 55, 65)}
        col = col_map.get(h_code, (150, 150, 150))
        if h_code == "none":
            pygame.draw.line(surf, RED, (cx - 10, cy - 10), (cx + 10, cy + 10), 3)
            pygame.draw.line(surf, RED, (cx + 10, cy - 10), (cx - 10, cy + 10), 3)
        else:
            pygame.draw.rect(surf, col, (cx - 14, cy - 13, 28, 14), border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.rect(surf, col, (cx - 14, cy + 1, 8, 13))
            pygame.draw.rect(surf, col, (cx + 6, cy + 1, 8, 13))
            pygame.draw.rect(surf, col, (cx - 2, cy + 1, 4, 8))
            if h_code == "diamond":
                pygame.draw.rect(surf, (200, 255, 255), (cx - 10, cy - 10, 4, 4))
            elif h_code == "iron":
                pygame.draw.rect(surf, WHITE, (cx - 10, cy - 10, 4, 4))
            pygame.draw.rect(surf, (30, 30, 30), (cx - 15, cy - 14, 30, 29), 1)

    elif item_type == "veh_pig":
        pygame.draw.rect(surf, (240, 145, 155), (cx - 14, cy - 12, 28, 24))
        pygame.draw.rect(surf, (225, 110, 125), (cx - 6, cy - 2, 12, 8))
        pygame.draw.rect(surf, (40, 30, 30), (cx - 4, cy + 1, 2, 2))
        pygame.draw.rect(surf, (40, 30, 30), (cx + 2, cy + 1, 2, 2))
        pygame.draw.rect(surf, WHITE, (cx - 10, cy - 7, 4, 4))
        pygame.draw.rect(surf, WHITE, (cx + 6, cy - 7, 4, 4))
    elif item_type == "veh_llama":
        pygame.draw.rect(surf, (230, 220, 200), (cx - 12, cy - 14, 24, 28))
        pygame.draw.rect(surf, (200, 185, 165), (cx - 7, cy - 4, 14, 12))
        pygame.draw.rect(surf, (50, 40, 40), (cx - 9, cy - 8, 3, 3))
        pygame.draw.rect(surf, (50, 40, 40), (cx + 6, cy - 8, 3, 3))
    elif item_type == "veh_boat":
        pygame.draw.polygon(surf, (140, 95, 55), [(cx - 18, cy + 2), (cx + 18, cy + 2), (cx + 12, cy + 14), (cx - 12, cy + 14)])
        pygame.draw.line(surf, (180, 140, 90), (cx - 8, cy - 8), (cx + 14, cy + 6), 3)
    elif item_type == "veh_strider":
        pygame.draw.rect(surf, (175, 45, 45), (cx - 14, cy - 14, 28, 26))
        pygame.draw.rect(surf, WHITE, (cx - 9, cy - 6, 4, 4))
        pygame.draw.rect(surf, WHITE, (cx + 5, cy - 6, 4, 4))
        pygame.draw.line(surf, (110, 25, 25), (cx - 14, cy - 2), (cx - 20, cy + 8), 2)
        pygame.draw.line(surf, (110, 25, 25), (cx + 14, cy - 2), (cx + 20, cy + 8), 2)
    elif item_type == "veh_dragon":
        pygame.draw.rect(surf, (25, 25, 28), (cx - 12, cy - 10, 24, 20))
        pygame.draw.rect(surf, (220, 60, 255), (cx - 8, cy - 6, 5, 4))
        pygame.draw.rect(surf, (220, 60, 255), (cx + 3, cy - 6, 5, 4))

    elif item_type == "sharp_sword":
        pygame.draw.line(surf, (50, 225, 220), (cx + 12, cy - 12), (cx - 2, cy + 2), 5)
        pygame.draw.rect(surf, (140, 95, 45), (cx - 6, cy + 6, 4, 4))
        pygame.draw.line(surf, (90, 60, 30), (cx - 6, cy + 6), (cx - 12, cy + 12), 3)
    elif item_type == "strength_potion":
        pygame.draw.rect(surf, (200, 40, 180), (cx - 8, cy - 4, 16, 16), border_radius=4)
        pygame.draw.rect(surf, (200, 200, 220), (cx - 4, cy - 12, 8, 8))
        pygame.draw.rect(surf, (160, 110, 60), (cx - 5, cy - 15, 10, 3))
    elif item_type == "dragon_bow":
        pygame.draw.arc(surf, (140, 90, 50), (cx - 14, cy - 14, 26, 28), -math.pi/2, math.pi/2, 3)
        pygame.draw.line(surf, (60, 220, 255), (cx - 1, cy - 14), (cx - 1, cy + 14), 2)
    elif item_type == "end_crystal":
        pygame.draw.rect(surf, (40, 40, 45), (cx - 12, cy + 8, 24, 6))
        pygame.draw.rect(surf, (210, 160, 245), (cx - 9, cy - 10, 18, 18), 2)
        pygame.draw.circle(surf, (230, 60, 255), (cx, cy - 1), 5)

    elif item_type == "totem":
        pygame.draw.rect(surf, (245, 190, 30), (cx - 6, cy - 12, 12, 24))
        pygame.draw.polygon(surf, (255, 220, 60), [(cx - 6, cy - 4), (cx - 16, cy - 10), (cx - 6, cy + 2)])
        pygame.draw.polygon(surf, (255, 220, 60), [(cx + 6, cy - 4), (cx + 16, cy - 10), (cx + 6, cy + 2)])
        pygame.draw.rect(surf, MC_EMERALD, (cx - 4, cy - 8, 3, 3))
        pygame.draw.rect(surf, MC_EMERALD, (cx + 1, cy - 8, 3, 3))
    elif item_type == "luck":
        pygame.draw.rect(surf, (50, 220, 80), (cx - 8, cy - 4, 16, 16), border_radius=4)
        pygame.draw.rect(surf, (200, 200, 220), (cx - 4, cy - 12, 8, 8))
        pygame.draw.rect(surf, (160, 110, 60), (cx - 5, cy - 15, 10, 3))
        pygame.draw.circle(surf, WHITE, (cx - 2, cy), 2)

content_box = pygame.Rect(140, 100, 740, 475)

def get_shop_row_rects(index, total_rows=4):
    spacing = 78 if total_rows <= 4 else 70
    row_y = content_box.y + 16 + index * spacing
    row_rect = pygame.Rect(content_box.x + 18, row_y, content_box.width - 36, 62)
    slot_rect = pygame.Rect(row_rect.x + 8, row_rect.y + 6, 50, 50)
    btn_rect = pygame.Rect(row_rect.right - 125, row_rect.y + 14, 115, 34)
    return row_rect, slot_rect, btn_rect

def draw_mob(surf, cx, cy, mob_id, anim_tick=0, flash_red=False):
    bob = int(math.sin(anim_tick * 0.15) * 3)
    cy += bob
    if mob_id == "creeper":
        c_col = (255, 100, 100) if flash_red else (70, 175, 60)
        pygame.draw.rect(surf, c_col, (cx - 16, cy - 28, 32, 32))
        eye_col = (40, 40, 40)
        pygame.draw.rect(surf, eye_col, (cx - 12, cy - 22, 8, 8))
        pygame.draw.rect(surf, eye_col, (cx + 4, cy - 22, 8, 8))
        pygame.draw.rect(surf, eye_col, (cx - 4, cy - 14, 8, 10))
        pygame.draw.rect(surf, eye_col, (cx - 8, cy - 8, 4, 10))
        pygame.draw.rect(surf, eye_col, (cx + 4, cy - 8, 4, 10))
        pygame.draw.rect(surf, c_col, (cx - 10, cy + 4, 20, 26))
        pygame.draw.rect(surf, (50, 140, 45), (cx - 16, cy + 30, 12, 12))
        pygame.draw.rect(surf, (50, 140, 45), (cx + 4, cy + 30, 12, 12))
    elif mob_id == "skeleton":
        s_col = (255, 100, 100) if flash_red else (210, 210, 215)
        pygame.draw.rect(surf, s_col, (cx - 15, cy - 26, 30, 28))
        pygame.draw.rect(surf, (30, 30, 30), (cx - 11, cy - 18, 8, 8))
        pygame.draw.rect(surf, (30, 30, 30), (cx + 3, cy - 18, 8, 8))
        pygame.draw.rect(surf, (40, 40, 40), (cx - 3, cy - 6, 6, 6))
        pygame.draw.rect(surf, (170, 170, 175), (cx - 8, cy + 2, 16, 26))
        pygame.draw.rect(surf, s_col, (cx - 8, cy + 28, 5, 16))
        pygame.draw.rect(surf, s_col, (cx + 3, cy + 28, 5, 16))
        pygame.draw.arc(surf, (130, 85, 45), (cx + 10, cy - 6, 16, 30), -math.pi/2, math.pi/2, 3)
    elif mob_id == "stray":
        s_col = (255, 100, 100) if flash_red else (160, 185, 200)
        pygame.draw.rect(surf, s_col, (cx - 15, cy - 26, 30, 28))
        pygame.draw.rect(surf, (60, 220, 240), (cx - 11, cy - 18, 8, 8))
        pygame.draw.rect(surf, (60, 220, 240), (cx + 3, cy - 18, 8, 8))
        pygame.draw.rect(surf, (70, 95, 115), (cx - 10, cy + 2, 20, 26))
        pygame.draw.rect(surf, s_col, (cx - 8, cy + 28, 5, 16))
        pygame.draw.rect(surf, s_col, (cx + 3, cy + 28, 5, 16))
    elif mob_id == "blaze":
        b_col = (255, 120, 120) if flash_red else (240, 185, 30)
        pygame.draw.rect(surf, b_col, (cx - 14, cy - 20, 28, 26))
        pygame.draw.rect(surf, (60, 20, 10), (cx - 10, cy - 14, 6, 6))
        pygame.draw.rect(surf, (60, 20, 10), (cx + 4, cy - 14, 6, 6))
        for i in range(4):
            angle = anim_tick * 0.1 + i * (math.pi / 2)
            rx = cx + int(math.cos(angle) * 26)
            ry = cy + int(math.sin(angle) * 12) + 10
            pygame.draw.rect(surf, (255, 120, 20), (rx - 3, ry - 12, 6, 24))
    elif mob_id == "enderman":
        e_col = (255, 100, 100) if flash_red else (20, 20, 25)
        pygame.draw.rect(surf, e_col, (cx - 12, cy - 44, 24, 24))
        pygame.draw.rect(surf, (200, 60, 245), (cx - 10, cy - 34, 7, 4))
        pygame.draw.rect(surf, (200, 60, 245), (cx + 3, cy - 34, 7, 4))
        pygame.draw.rect(surf, WHITE, (cx - 8, cy - 33, 3, 2))
        pygame.draw.rect(surf, WHITE, (cx + 5, cy - 33, 3, 2))
        pygame.draw.rect(surf, e_col, (cx - 6, cy - 20, 12, 34))
        pygame.draw.rect(surf, e_col, (cx - 14, cy - 16, 4, 46))
        pygame.draw.rect(surf, e_col, (cx + 10, cy - 16, 4, 46))
        pygame.draw.rect(surf, e_col, (cx - 5, cy + 14, 4, 34))
        pygame.draw.rect(surf, e_col, (cx + 1, cy + 14, 4, 34))
    elif mob_id in ("zombie", "husk", "piglin"):
        colors = {
            "zombie": ((75, 155, 80), (55, 95, 145)),
            "husk": ((175, 145, 85), (115, 85, 45)),
            "piglin": ((235, 155, 145), (105, 55, 65)),
        }
        head_col, body_col = colors[mob_id]
        if flash_red:
            head_col = (255, 100, 100)
        pygame.draw.rect(surf, head_col, (cx - 15, cy - 27, 30, 28))
        pygame.draw.rect(surf, (25, 25, 25), (cx - 10, cy - 18, 6, 6))
        pygame.draw.rect(surf, (25, 25, 25), (cx + 4, cy - 18, 6, 6))
        if mob_id == "piglin":
            pygame.draw.rect(surf, head_col, (cx - 21, cy - 22, 6, 14))
            pygame.draw.rect(surf, head_col, (cx + 15, cy - 22, 6, 14))
        pygame.draw.rect(surf, body_col, (cx - 12, cy + 1, 24, 28))
        pygame.draw.rect(surf, head_col, (cx - 20, cy + 3, 8, 24))
        pygame.draw.rect(surf, head_col, (cx + 12, cy + 3, 8, 24))
        pygame.draw.rect(surf, body_col, (cx - 10, cy + 29, 8, 15))
        pygame.draw.rect(surf, body_col, (cx + 2, cy + 29, 8, 15))
    elif mob_id in ("spider", "cave_spider"):
        body_col = (255, 100, 100) if flash_red else ((45, 45, 50) if mob_id == "spider" else (35, 80, 100))
        pygame.draw.rect(surf, body_col, (cx - 20, cy - 8, 40, 22), border_radius=5)
        pygame.draw.rect(surf, body_col, (cx - 14, cy - 22, 28, 18), border_radius=4)
        eye_col = (220, 35, 35) if mob_id == "spider" else (80, 220, 255)
        for eye_x in (-9, -3, 4, 10):
            pygame.draw.rect(surf, eye_col, (cx + eye_x - 2, cy - 17, 4, 4))
        for side in (-1, 1):
            for leg_y in (-5, 4, 13):
                pygame.draw.line(surf, body_col, (cx + side * 14, cy + leg_y), (cx + side * 31, cy + leg_y + 8), 4)
    elif mob_id == "witch":
        w_col = (255, 100, 100) if flash_red else (115, 75, 135)
        pygame.draw.rect(surf, (105, 135, 75), (cx - 14, cy - 22, 28, 26))
        pygame.draw.rect(surf, (40, 25, 45), (cx - 20, cy - 28, 40, 7))
        pygame.draw.polygon(surf, (50, 30, 55), [(cx - 13, cy - 28), (cx + 13, cy - 28), (cx, cy - 49)])
        pygame.draw.rect(surf, (45, 25, 45), (cx - 3, cy - 14, 6, 12))
        pygame.draw.rect(surf, w_col, (cx - 15, cy + 4, 30, 38))
    elif mob_id == "snow_golem":
        snow_col = (255, 140, 140) if flash_red else (235, 245, 250)
        pygame.draw.circle(surf, snow_col, (cx, cy + 17), 22)
        pygame.draw.circle(surf, snow_col, (cx, cy - 15), 16)
        pygame.draw.rect(surf, (235, 110, 25), (cx, cy - 14, 18, 5))
        pygame.draw.rect(surf, (30, 30, 30), (cx - 9, cy - 21, 4, 4))
        pygame.draw.rect(surf, (30, 30, 30), (cx + 5, cy - 21, 4, 4))
        pygame.draw.line(surf, (120, 85, 50), (cx - 18, cy + 4), (cx - 32, cy - 5), 3)
        pygame.draw.line(surf, (120, 85, 50), (cx + 18, cy + 4), (cx + 32, cy - 5), 3)
    elif mob_id == "magma_cube":
        m_col = (255, 130, 130) if flash_red else (110, 25, 20)
        stretch = abs(int(math.sin(anim_tick * 0.16) * 5))
        pygame.draw.rect(surf, m_col, (cx - 22, cy - 15 - stretch, 44, 38 + stretch), border_radius=3)
        pygame.draw.rect(surf, (240, 95, 20), (cx - 22, cy + 7, 44, 6))
        pygame.draw.rect(surf, (255, 190, 35), (cx - 13, cy - 5, 8, 6))
        pygame.draw.rect(surf, (255, 190, 35), (cx + 5, cy - 5, 8, 6))
    elif mob_id == "shulker":
        shell_col = (255, 120, 150) if flash_red else (150, 90, 170)
        pygame.draw.rect(surf, shell_col, (cx - 22, cy - 18, 44, 42), border_radius=4)
        pygame.draw.rect(surf, (95, 55, 115), (cx - 18, cy - 12, 36, 11))
        pygame.draw.rect(surf, (45, 30, 55), (cx - 12, cy + 2, 24, 17))
        pygame.draw.rect(surf, (220, 210, 80), (cx - 6, cy + 7, 12, 5))
    elif mob_id == "endermite":
        mite_col = (255, 110, 130) if flash_red else (90, 65, 115)
        for segment in range(4):
            sx = cx - 24 + segment * 14
            sy = cy + int(math.sin(anim_tick * 0.2 + segment) * 4)
            pygame.draw.rect(surf, mite_col, (sx, sy - 7, 16, 14), border_radius=4)
            pygame.draw.line(surf, (180, 100, 220), (sx + 5, sy - 7), (sx + 1, sy - 14), 2)

def draw_sage_fouras(surf, cx, cy, anim_tick=0):
    """Original pixel-art sage inspired by a mysterious fortress riddler."""
    bob = int(math.sin(anim_tick * 0.08) * 2)
    cy += bob
    robe = (75, 65, 105)
    robe_light = (105, 90, 135)
    skin = (220, 175, 135)
    hair = (225, 225, 215)
    pygame.draw.polygon(surf, robe, [(cx - 24, cy + 42), (cx + 24, cy + 42), (cx + 14, cy - 2), (cx - 14, cy - 2)])
    pygame.draw.rect(surf, robe_light, (cx - 8, cy + 8, 16, 28))
    pygame.draw.rect(surf, skin, (cx - 16, cy - 30, 32, 30))
    pygame.draw.rect(surf, hair, (cx - 19, cy - 34, 38, 9))
    pygame.draw.rect(surf, hair, (cx - 20, cy - 27, 7, 25))
    pygame.draw.rect(surf, hair, (cx + 13, cy - 27, 7, 25))
    pygame.draw.rect(surf, (45, 45, 55), (cx - 10, cy - 19, 5, 4))
    pygame.draw.rect(surf, (45, 45, 55), (cx + 5, cy - 19, 5, 4))
    pygame.draw.polygon(surf, hair, [(cx - 13, cy - 4), (cx + 13, cy - 4), (cx, cy + 20)])
    pygame.draw.line(surf, (120, 80, 45), (cx + 22, cy - 2), (cx + 29, cy + 43), 4)
    pygame.draw.circle(surf, MC_GOLD, (cx + 22, cy - 5), 5)

def draw_ender_dragon_boss(surf, cx, cy, anim_tick=0, flash_red=False):
    wing_flap = int(math.sin(anim_tick * 0.22) * 24)
    d_col = (255, 100, 100) if flash_red else (20, 20, 24)
    pygame.draw.polygon(surf, (40, 35, 45), [(cx - 20, cy), (cx - 110, cy - 45 + wing_flap), (cx - 40, cy + 25)])
    pygame.draw.polygon(surf, (40, 35, 45), [(cx + 20, cy), (cx + 110, cy - 45 + wing_flap), (cx + 40, cy + 25)])
    pygame.draw.line(surf, (15, 15, 20), (cx, cy), (cx - 110, cy - 45 + wing_flap), 4)
    pygame.draw.line(surf, (15, 15, 20), (cx, cy), (cx + 110, cy - 45 + wing_flap), 4)
    pygame.draw.rect(surf, d_col, (cx - 25, cy - 15, 50, 40), border_radius=4)
    pygame.draw.rect(surf, d_col, (cx - 8, cy + 25, 16, 35))
    pygame.draw.rect(surf, (45, 40, 50), (cx - 12, cy + 50, 24, 10))
    pygame.draw.rect(surf, d_col, (cx - 12, cy - 42, 24, 30))
    pygame.draw.rect(surf, d_col, (cx - 22, cy - 70, 44, 32))
    pygame.draw.rect(surf, (10, 10, 15), (cx - 16, cy - 50, 32, 12))
    pygame.draw.rect(surf, (220, 60, 255), (cx - 18, cy - 64, 10, 6))
    pygame.draw.rect(surf, (220, 60, 255), (cx + 8, cy - 64, 10, 6))
    pygame.draw.rect(surf, WHITE, (cx - 14, cy - 63, 4, 4))
    pygame.draw.rect(surf, WHITE, (cx + 10, cy - 63, 4, 4))

def draw_steve_animated(surf, cx, cy, v_type, is_upgraded, helmet="none", anim_tick=0, is_moving=False, squash=1.0, sword_swing=0):
    walk_cycle = math.sin(anim_tick * 0.25) if is_moving else math.sin(anim_tick * 0.06) * 0.4
    leg_swing = int(walk_cycle * 6)
    cy += int((1.0 - squash) * 15)

    if v_type == "pig":
        pygame.draw.rect(surf, (240, 145, 155), (cx - 22, cy + 8, 44, 22))
        pygame.draw.rect(surf, (245, 170, 180), (cx + 14, cy + 4, 14, 14))
        pygame.draw.rect(surf, (225, 110, 125), (cx + 22, cy + 10, 8, 6))
        pygame.draw.rect(surf, (215, 125, 135), (cx - 18 + leg_swing, cy + 30, 8, 10))
        pygame.draw.rect(surf, (215, 125, 135), (cx + 6 - leg_swing, cy + 30, 8, 10))
        pygame.draw.rect(surf, (135, 75, 35), (cx - 10, cy + 6, 20, 8))
        if is_upgraded:
            pygame.draw.rect(surf, (60, 220, 210), (cx - 22, cy + 12, 44, 8), 2)
        rod_tip = (cx + 34, cy - 14)
        pygame.draw.line(surf, (140, 95, 45), (cx + 8, cy - 4), rod_tip, 3)
        carrot_pos = (rod_tip[0] + 4, rod_tip[1] + 16 + int(math.sin(anim_tick * 0.2) * 3))
        pygame.draw.line(surf, (200, 200, 200), rod_tip, carrot_pos, 1)
        pygame.draw.polygon(surf, (255, 120, 20), [carrot_pos, (carrot_pos[0]+5, carrot_pos[1]-4), (carrot_pos[0]+2, carrot_pos[1]+6)])
        pygame.draw.rect(surf, (50, 180, 40), (carrot_pos[0], carrot_pos[1]-6, 4, 3))
    elif v_type == "llama":
        neck_bob = int(walk_cycle * 2)
        pygame.draw.rect(surf, (230, 220, 200), (cx - 18, cy + 4, 36, 26))
        pygame.draw.rect(surf, (230, 220, 200), (cx + 10, cy - 14 + neck_bob, 12, 24))
        pygame.draw.rect(surf, (210, 195, 175), (cx + 16, cy - 14 + neck_bob, 10, 10))
        pygame.draw.rect(surf, (190, 175, 155), (cx - 14 + leg_swing, cy + 30, 7, 12))
        pygame.draw.rect(surf, (190, 175, 155), (cx + 8 - leg_swing, cy + 30, 7, 12))
        popona_col = (70, 170, 230) if is_upgraded else (190, 50, 40)
        pygame.draw.rect(surf, popona_col, (cx - 12, cy + 4, 24, 18))
    elif v_type == "boat":
        pygame.draw.polygon(surf, (130, 85, 45), [(cx - 26, cy + 14), (cx + 26, cy + 14), (cx + 20, cy + 30), (cx - 20, cy + 30)])
        oar_angle = math.sin(anim_tick * 0.3) * 0.5 if is_moving else -0.3
        oar_dx, oar_dy = int(math.cos(oar_angle) * 16), int(math.sin(oar_angle) * 16)
        pygame.draw.line(surf, (170, 125, 75), (cx + 2, cy + 18), (cx + 2 + oar_dx, cy + 18 + oar_dy), 3)
        pygame.draw.rect(surf, (150, 105, 55), (cx + oar_dx, cy + 16 + oar_dy, 6, 8))
        if is_upgraded:
            pygame.draw.rect(surf, (160, 110, 55), (cx - 22, cy + 6, 14, 14))
            pygame.draw.rect(surf, (30, 30, 30), (cx - 16, cy + 11, 3, 4))
    elif v_type == "strider":
        pygame.draw.rect(surf, (175, 45, 45), (cx - 18, cy - 4, 36, 32))
        pygame.draw.line(surf, (110, 25, 25), (cx - 18, cy + 8), (cx - 26 + leg_swing//2, cy + 14), 3)
        pygame.draw.line(surf, (110, 25, 25), (cx + 18, cy + 8), (cx + 26 - leg_swing//2, cy + 14), 3)
        leg_strider = int(walk_cycle * 9)
        pygame.draw.rect(surf, (125, 30, 30), (cx - 12 + leg_strider, cy + 28, 7, 18))
        pygame.draw.rect(surf, (125, 30, 30), (cx + 5 - leg_strider, cy + 28, 7, 18))
    elif v_type == "dragon":
        wing_flap = int(math.sin(anim_tick * 0.2) * 14)
        if is_upgraded:
            pygame.draw.rect(surf, (25, 25, 28), (cx - 22, cy + 12, 44, 14))
            pygame.draw.polygon(surf, (45, 35, 55), [(cx - 10, cy + 12), (cx - 38, cy - 8 + wing_flap), (cx - 15, cy + 8)])
            pygame.draw.polygon(surf, (45, 35, 55), [(cx + 10, cy + 12), (cx + 38, cy - 8 + wing_flap), (cx + 15, cy + 8)])
            pygame.draw.circle(surf, (215, 75, 240), (cx + 22, cy + 14), 3)
        else:
            pygame.draw.polygon(surf, (70, 70, 85), [(cx - 6, cy + 4), (cx - 26, cy + 24 + wing_flap//2), (cx - 10, cy + 26)])
            pygame.draw.polygon(surf, (70, 70, 85), [(cx + 6, cy + 4), (cx + 26, cy + 24 + wing_flap//2), (cx + 10, cy + 26)])

    sx, sy = cx, cy - 14 + int(walk_cycle * 1.5)
    pygame.draw.rect(surf, (55, 35, 20), (sx - 12, sy - 14, 24, 7))
    pygame.draw.rect(surf, (195, 140, 100), (sx - 12, sy - 7, 24, 17))
    pygame.draw.rect(surf, WHITE, (sx - 9, sy - 3, 5, 4))
    pygame.draw.rect(surf, (60, 50, 145), (sx - 6, sy - 3, 3, 4))
    pygame.draw.rect(surf, WHITE, (sx + 4, sy - 3, 5, 4))
    pygame.draw.rect(surf, (60, 50, 145), (sx + 4, sy - 3, 3, 4))
    pygame.draw.rect(surf, (155, 95, 65), (sx - 3, sy + 2, 6, 3))
    pygame.draw.rect(surf, (90, 50, 30), (sx - 5, sy + 6, 10, 2))
    pygame.draw.rect(surf, (0, 165, 175), (sx - 10, sy + 10, 20, 12))

    if sword_swing > 0:
        blade_angle = math.radians(45 - sword_swing * 6)
        bx = sx + 14 + int(math.cos(blade_angle) * 24)
        by = sy + int(math.sin(blade_angle) * 24)
        pygame.draw.line(surf, (50, 220, 210), (sx + 12, sy + 8), (bx, by), 5)
        pygame.draw.line(surf, (140, 95, 45), (sx + 12, sy + 8), (sx + 8, sy + 12), 4)
    else:
        pygame.draw.line(surf, (50, 220, 210), (sx + 14, sy + 4), (sx + 26, sy - 12), 4)
        pygame.draw.line(surf, (140, 95, 45), (sx + 12, sy + 6), (sx + 10, sy + 10), 3)

    h_col = HELMETS.get(helmet, {}).get("color")
    if h_col:
        pygame.draw.rect(surf, h_col, (sx - 13, sy - 16, 26, 11))
        pygame.draw.rect(surf, h_col, (sx - 13, sy - 16, 6, 18))
        pygame.draw.rect(surf, h_col, (sx + 7, sy - 16, 6, 18))
        pygame.draw.rect(surf, (30, 30, 30), (sx - 13, sy - 16, 26, 18), 1)

# ==================== ПЕРЕМЕННЫЕ И СОСТОЯНИЕ ====================
TOTAL_QUESTS = 50
STEPS_PER_WORLD = 10
base_y = 490
platforms = [(95 + i * ((WIDTH - 190) // STEPS_PER_WORLD), base_y) for i in range(STEPS_PER_WORLD + 1)]

last_player_name = get_last_player()
player_name = last_player_name if last_player_name in PLAYER_PROFILES else "Ксения"
player_data = get_player(player_name, apply_daily_bonus=False)
sound_enabled = player_data.get("sound_enabled", True)
game_state = "LOGIN"

task_num = player_data.get("task_num", 1) if player_data else 1
combo_count = 0
current_world_idx = min((task_num - 1) // STEPS_PER_WORLD, 4)
step_in_world = (task_num - 1) % STEPS_PER_WORLD

hero_x = float(platforms[step_in_world][0])
hero_y = float(platforms[step_in_world][1] - 24)
target_x, target_y = hero_x, hero_y
is_moving = False
move_progress = 0.0
squash_val = 1.0
anim_tick = 0
sword_swing_timer = 0
mob_flash_timer = 0

ten_errors = []
question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])
message = "Добудь правильный ответ!"
message_color = DARK_TEXT

# Переменные моба
mob_max_hp = 3
mob_hp = 3
mob_task_str = ""
mob_ans = 0
mob_choices = []
mob_clean_expr = ""
mob_op = "+"
mob_battle_result_msg = ""
mob_failed_reset = False

# Переменные финального босса
boss_max_hp = 5
boss_streak = 0
boss_task_str = ""
boss_ans = 0
boss_choices = []
boss_op = "+"
boss_clean_expr = ""
boss_msg = "Победи Дракона!"
boss_won = False
boss_review_queue = []
boss_is_review = False

# Переменные Старца Фура
sage_question = ""
sage_answer = None
sage_choices = []
sage_msg = "Отгадай загадку с первой попытки!"
sage_won = False
sage_reward_name = ""
stats_page = 0
STATS_PER_PAGE = 6
history_page = 0
history_selected_index = None
HISTORY_PER_PAGE = 5

workbench_tab = "HELMETS"

particles = []
floating_texts = []

def spawn_dust(x, y, color=(160, 150, 140)):
    for _ in range(3):
        particles.append([
            x + random.randint(-8, 8), y + random.randint(-3, 3),
            random.uniform(-1.5, 1.5), random.uniform(-1.8, -0.4),
            color, random.randint(15, 25), random.randint(3, 5)
        ])

def spawn_hit_sparks(x, y, is_shield=False):
    col_choices = [(80, 240, 255), (255, 230, 50)] if is_shield else [(255, 80, 40), (255, 230, 50)]
    for _ in range(16 if is_shield else 12):
        particles.append([
            x + random.randint(-8, 8), y + random.randint(-12, 12),
            random.uniform(-3.5, 3.5), random.uniform(-3.5, 2.5),
            random.choice(col_choices),
            random.randint(16, 28), random.randint(4, 7)
        ])

def spawn_speed_bubbles(x, y):
    if random.random() < 0.35:
        particles.append([
            x + random.randint(-15, 15), y + random.randint(-10, 10),
            random.uniform(-0.4, 0.4), random.uniform(-1.5, -0.6),
            (80, 255, 120), random.randint(20, 35), random.randint(2, 4)
        ])

def get_mob_max_hp():
    arts = player_data.get("artifacts", []) if player_data else []
    if "strength_potion" in arts:
        return 1
    if "sharp_sword" in arts:
        return 2
    return 3

def get_boss_max_hp():
    arts = player_data.get("artifacts", []) if player_data else []
    if "end_crystal" in arts:
        base_hp = 3
    elif "dragon_bow" in arts:
        base_hp = 4
    else:
        base_hp = 5
    return base_hp + (player_data.get("boss_penalty_errors", 0) if player_data else 0)

def start_mob_encounter():
    global game_state, mob_hp, mob_max_hp, mob_task_str, mob_ans, mob_choices, mob_clean_expr, mob_op
    global mob_battle_result_msg, mob_failed_reset

    game_state = "MOB_BATTLE"
    mob_max_hp = get_mob_max_hp()
    mob_hp = mob_max_hp
    mob_failed_reset = False
    mob_battle_result_msg = "Реши пример, чтобы нанести удар!"
    route_ops = get_route_world(player_data, current_world_idx)["ops"]
    mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(route_ops)

def start_boss_battle():
    global game_state, boss_streak, boss_max_hp
    global boss_msg, boss_won, boss_review_queue

    game_state = "BOSS_BATTLE"
    boss_max_hp = get_boss_max_hp()
    boss_streak = 0
    boss_won = False
    boss_review_queue = [
        dict(error) for error in player_data.get("marathon_error_details", [])
    ]
    error_penalty = player_data.get("boss_penalty_errors", 0) if player_data else 0
    boss_msg = f"Нужно {boss_max_hp} верных ответов подряд (ошибки марафона: +{error_penalty})!"
    set_next_boss_task()

def set_next_boss_task():
    global boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr, boss_is_review
    if boss_streak < len(boss_review_queue):
        boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_review_task(
            boss_review_queue[boss_streak]
        )
        boss_is_review = True
    else:
        boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_math_task(["+", "-", "*", "/"])
        boss_is_review = False

def start_sage_encounter():
    global game_state, sage_question, sage_answer, sage_choices, sage_msg, sage_won, sage_reward_name
    game_state = "SAGE_CHALLENGE"
    sage_question, sage_answer, sage_choices = pick_logic_task(player_name)
    sage_msg = "Одна попытка на загадку. Ошибёшься — получишь новую!"
    sage_won = False
    sage_reward_name = ""

def reset_entire_marathon():
    global task_num, step_in_world, current_world_idx, hero_x, hero_y, target_x, target_y, is_moving
    global ten_errors, question_str, correct_ans, choices, current_op, clean_expr, game_state, message, message_color
    global player_data

    task_num = 1
    step_in_world = 0
    current_world_idx = 0
    hero_x = float(platforms[0][0])
    hero_y = float(platforms[0][1] - 24)
    target_x, target_y = hero_x, hero_y
    is_moving = False
    ten_errors = []

    all_data = load_data()
    if player_name.strip() in all_data:
        p = all_data[player_name.strip()]
        p["task_num"] = 1
        p["marathon_errors"] = 0
        p["marathon_error_details"] = []
        p["boss_penalty_errors"] = 0
        p["helmet_protections"] = 0
        p["marathon_route"] = create_marathon_route(player_name)
        p["treasure_tasks"] = create_treasure_tasks()
        p["sage_task"] = create_sage_task(p["marathon_route"])
        p["sage_completed"] = False
        p["sage_artifact"] = None
        save_data(all_data)
        player_data = p

    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, 0)["ops"])
    message = "Марафон начат сначала! Вперёд!"
    message_color = DARK_TEXT
    game_state = "GAME"

# Кнопки
btn_w, btn_h = 140, 54
start_btn_x = (WIDTH - (3 * btn_w + 40)) // 2
answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 235, btn_w, btn_h) for i in range(3)]
mob_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]
boss_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]
sage_answer_buttons = [pygame.Rect(130 + i * 250, 370, 230, 58) for i in range(3)]
sage_continue_btn = pygame.Rect(WIDTH // 2 - 145, 470, 290, 48)

nav_workbench = pygame.Rect(WIDTH - 505, 10, 105, 34)
nav_players = pygame.Rect(WIDTH - 395, 10, 85, 34)
nav_sound = pygame.Rect(WIDTH - 305, 10, 90, 34)
nav_reset_game = pygame.Rect(WIDTH - 210, 10, 90, 34)
nav_fullscreen = pygame.Rect(WIDTH - 105, 10, 90, 34)

confirm_reset_yes = pygame.Rect(WIDTH // 2 - 130, 310, 110, 42)
confirm_reset_no = pygame.Rect(WIDTH // 2 + 20, 310, 110, 42)

player_play_buttons = {
    "Ксения": pygame.Rect(WIDTH // 2 - 105, 245, 150, 44),
    "Настя": pygame.Rect(WIDTH // 2 - 105, 330, 150, 44),
}
player_stats_buttons = {
    "Ксения": pygame.Rect(WIDTH // 2 + 55, 245, 150, 44),
    "Настя": pygame.Rect(WIDTH // 2 + 55, 330, 150, 44),
}

mob_btn_continue = pygame.Rect(WIDTH // 2 - 145, 475, 290, 48)
boss_btn_finish = pygame.Rect(WIDTH // 2 - 150, 475, 300, 48)
review_btn_continue = pygame.Rect(WIDTH // 2 - 160, 500, 320, 48)
final_win_restart_btn = pygame.Rect(WIDTH // 2 - 140, 385, 280, 46)
stats_prev_btn = pygame.Rect(WIDTH // 2 - 250, 500, 120, 42)
stats_next_btn = pygame.Rect(WIDTH // 2 + 130, 500, 120, 42)
stats_restart_btn = pygame.Rect(WIDTH // 2 - 120, 500, 240, 42)
history_back_btn = pygame.Rect(145, 520, 130, 40)
history_prev_btn = pygame.Rect(WIDTH // 2 - 150, 520, 110, 40)
history_next_btn = pygame.Rect(WIDTH // 2 + 40, 520, 110, 40)
history_detail_buttons = [pygame.Rect(720, 125 + i * 72, 120, 36) for i in range(HISTORY_PER_PAGE)]

tab_helmets_rect = pygame.Rect(140, 55, 170, 36)
tab_vehicles_rect = pygame.Rect(325, 55, 175, 36)
tab_artifacts_rect = pygame.Rect(515, 55, 175, 36)
tab_potions_rect = pygame.Rect(705, 55, 175, 36)

# ==================== ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ ====================
async def main():
    global player_name, player_data, game_state, task_num, combo_count, current_world_idx, step_in_world
    global hero_x, hero_y, target_x, target_y, is_moving, move_progress, squash_val, anim_tick
    global sword_swing_timer, mob_flash_timer, ten_errors, question_str, correct_ans, choices, current_op, clean_expr
    global message, message_color, mob_hp, mob_task_str, mob_ans, mob_choices, mob_clean_expr, mob_op
    global mob_battle_result_msg, mob_failed_reset, boss_streak
    global boss_msg, boss_won, workbench_tab, stats_page, sound_enabled
    global history_page, history_selected_index
    global sage_question, sage_answer, sage_choices, sage_msg, sage_won, sage_reward_name

    running = True

    while running:
        anim_tick += 1
        mouse_pos = pygame.mouse.get_pos()

        if sword_swing_timer > 0: sword_swing_timer -= 1
        if mob_flash_timer > 0: mob_flash_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and hasattr(event, "pos"):
                mouse_pos = event.pos
                ensure_audio()

            if event.type == pygame.QUIT:
                running = False

            elif game_state == "LOGIN":
                selected_for_play = None
                selected_for_stats = None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for profile_name in PLAYER_PROFILES:
                        if player_play_buttons[profile_name].collidepoint(mouse_pos):
                            selected_for_play = profile_name
                        elif player_stats_buttons[profile_name].collidepoint(mouse_pos):
                            selected_for_stats = profile_name

                if selected_for_play:
                    player_name = selected_for_play
                    request_browser_fullscreen()
                    player_data = get_player(player_name)
                    sound_enabled = player_data.get("sound_enabled", True)
                    task_num = player_data.get("task_num", 1)
                    current_world_idx = min((task_num - 1) // STEPS_PER_WORLD, 4)
                    step_in_world = (task_num - 1) % STEPS_PER_WORLD
                    hero_x = float(platforms[step_in_world][0])
                    hero_y = float(platforms[step_in_world][1] - 24)
                    target_x, target_y = hero_x, hero_y
                    ten_errors = []
                    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])
                    game_state = "GAME"
                    if (
                        not player_data.get("sage_completed", False)
                        and player_data.get("sage_task") is not None
                        and task_num == player_data["sage_task"] + 1
                    ):
                        start_sage_encounter()
                elif selected_for_stats:
                    player_name = selected_for_stats
                    player_data = get_player(player_name, apply_daily_bonus=False)
                    sound_enabled = player_data.get("sound_enabled", True)
                    history_page = 0
                    history_selected_index = None
                    game_state = "HISTORY"

            elif game_state == "GAME":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if nav_fullscreen.collidepoint(mouse_pos):
                        request_browser_fullscreen()
                        continue
                    if nav_workbench.collidepoint(mouse_pos):
                        game_state = "WORKBENCH"
                        continue
                    if nav_players.collidepoint(mouse_pos):
                        game_state = "LOGIN"
                        continue
                    if nav_sound.collidepoint(mouse_pos):
                        sound_enabled = not sound_enabled
                        all_data = load_data()
                        p = all_data[player_name.strip()]
                        p["sound_enabled"] = sound_enabled
                        save_data(all_data)
                        player_data = p
                        if sound_enabled:
                            play_sound("correct")
                        continue
                    if nav_reset_game.collidepoint(mouse_pos):
                        game_state = "CONFIRM_RESET"
                        continue

                    if task_num > TOTAL_QUESTS:
                        if final_win_restart_btn.collidepoint(mouse_pos):
                            reset_entire_marathon()
                        continue

                    if not is_moving and task_num <= TOTAL_QUESTS:
                        for i, rect in enumerate(answer_buttons):
                            if rect.collidepoint(mouse_pos):
                                all_data = load_data()
                                p = all_data[player_name.strip()]

                                if choices[i] == correct_ans:
                                    play_sound("correct")
                                    combo_count += 1
                                    gain = 2 if combo_count >= 5 else 1
                                    is_treasure_task = task_num in p.get("treasure_tasks", [])
                                    if is_treasure_task:
                                        gain += 2
                                    if p.get("luck_timer", 0) > 0:
                                        gain *= 2
                                        p["luck_timer"] -= 1

                                    p["emeralds"] += gain
                                    floating_texts.append([f"+{gain} ИЗУМРУД!", hero_x, hero_y - 25, MC_EMERALD, 45])
                                    
                                    step_in_world += 1
                                    target_x = platforms[step_in_world][0]
                                    target_y = platforms[step_in_world][1] - 24
                                    is_moving = True
                                    move_progress = 0.0

                                    if is_treasure_task:
                                        message = f"СОКРОВИЩЕ НАЙДЕНО! (+{gain} изумр.)"
                                        message_color = MC_GOLD
                                    elif combo_count >= 5:
                                        message = f"СЕРИЯ x{combo_count} БЕЗ ОШИБОК! (+{gain} изумр.)"
                                        message_color = MC_GOLD
                                    else:
                                        message = f"Верно скрафчено! (+{gain} изумр.)"
                                        message_color = GREEN

                                    if task_num == TOTAL_QUESTS:
                                        task_num += 1
                                        p["task_num"] = task_num
                                        save_data(all_data)
                                        player_data = p
                                    elif task_num % STEPS_PER_WORLD == 0:
                                        task_num += 1
                                        p["task_num"] = task_num
                                        save_data(all_data)
                                        player_data = p
                                    else:
                                        task_num += 1
                                        p["task_num"] = task_num
                                        save_data(all_data)
                                        player_data = p
                                        question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])

                                else:
                                    wrong_val = choices[i]
                                    p["marathon_errors"] = p.get("marathon_errors", 0) + 1
                                    helmet_save = use_helmet_protection(p)
                                    if helmet_save:
                                        play_sound("hit")
                                    else:
                                        play_sound("wrong")
                                        p["boss_penalty_errors"] = p.get("boss_penalty_errors", 0) + 1
                                    p.setdefault("marathon_error_details", []).append({
                                        "world": current_world_idx + 1,
                                        "task": task_num,
                                        "expr": clean_expr,
                                        "wrong": wrong_val,
                                        "correct": correct_ans,
                                        "protected_by_helmet": bool(helmet_save)
                                    })
                                    save_data(all_data)
                                    player_data = p
                                    ten_errors.append({
                                        "expr": clean_expr,
                                        "wrong": wrong_val,
                                        "correct": correct_ans,
                                        "protected_by_helmet": bool(helmet_save)
                                    })
                                    combo_count = 0
                                    if helmet_save and helmet_save["broken"]:
                                        message = f"{helmet_save['helmet_name']} сломался! Ошибка не усилила Дракона."
                                        message_color = MC_GOLD
                                    elif helmet_save:
                                        message = f"Шлем защитил! Прочность: {helmet_save['remaining']} из {helmet_save['maximum']}"
                                        message_color = MC_GOLD
                                    else:
                                        message = "Ой, крипер взорвал ответ! Дракон стал сильнее."
                                        message_color = RED
                                    spawn_dust(hero_x, hero_y, color=(80, 80, 80))

            elif game_state == "CONFIRM_RESET":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if confirm_reset_yes.collidepoint(mouse_pos):
                        reset_entire_marathon()
                    elif confirm_reset_no.collidepoint(mouse_pos):
                        game_state = "GAME"

            elif game_state == "SAGE_CHALLENGE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if sage_won:
                        if sage_continue_btn.collidepoint(mouse_pos):
                            game_state = "GAME"
                    else:
                        for i, rect in enumerate(sage_answer_buttons):
                            if rect.collidepoint(mouse_pos):
                                if sage_choices[i] == sage_answer:
                                    all_data = load_data()
                                    p = all_data[player_name.strip()]
                                    available_artifacts = [
                                        artifact_id for artifact_id in ARTIFACTS
                                        if artifact_id not in p.get("artifacts", [])
                                    ]
                                    if available_artifacts:
                                        reward_id = random.choice(available_artifacts)
                                        p.setdefault("artifacts", []).append(reward_id)
                                        p["sage_artifact"] = reward_id
                                        sage_reward_name = ARTIFACTS[reward_id]["name"]
                                    else:
                                        p["sage_artifact"] = "collection_complete"
                                        sage_reward_name = "Все артефакты уже собраны"
                                    p["sage_completed"] = True
                                    save_data(all_data)
                                    player_data = p
                                    sage_won = True
                                    sage_msg = f"Верно! Награда: {sage_reward_name}"
                                    play_sound("victory")
                                else:
                                    previous_question = sage_question
                                    sage_question, sage_answer, sage_choices = pick_logic_task(
                                        player_name, previous_question
                                    )
                                    sage_msg = "Ответ неверный — эта загадка потеряна. Вот новая!"
                                    play_sound("wrong")
                                break

            elif game_state == "BOSS_BATTLE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if boss_won:
                        if boss_btn_finish.collidepoint(mouse_pos):
                            stats_page = 0
                            game_state = "FINAL_STATS"
                    else:
                        for i, rect in enumerate(boss_answer_buttons):
                            if rect.collidepoint(mouse_pos):
                                all_data = load_data()
                                p = all_data[player_name.strip()]

                                if boss_choices[i] == boss_ans:
                                    boss_streak += 1
                                    sword_swing_timer = 12
                                    mob_flash_timer = 10
                                    spawn_hit_sparks(720, 160)

                                    if boss_streak >= boss_max_hp:
                                        play_sound("victory")
                                        boss_won = True
                                        boss_msg = "ДРАКОН КРАЯ ПОВЕРЖЕН!"
                                        p["emeralds"] += 50
                                        p.setdefault("game_history", []).append({
                                            "completed_at": datetime.now().isoformat(timespec="minutes"),
                                            "errors": p.get("marathon_errors", 0),
                                            "boss_penalty_errors": p.get("boss_penalty_errors", 0),
                                            "helmet_protections": p.get("helmet_protections", 0),
                                            "error_details": [dict(item) for item in p.get("marathon_error_details", [])],
                                            "boss_hp": boss_max_hp,
                                            "grade": PLAYER_PROFILES.get(player_name, {}).get("grade"),
                                            "sage_artifact": p.get("sage_artifact"),
                                        })
                                        save_data(all_data)
                                        player_data = p
                                    else:
                                        play_sound("hit")
                                        boss_msg = f"Точный удар! Серия: {boss_streak} из {boss_max_hp}!"
                                        set_next_boss_task()
                                else:
                                    play_sound("wrong")
                                    if p.get("totems", 0) > 0:
                                        p["totems"] -= 1
                                        save_data(all_data)
                                        player_data = p
                                        spawn_hit_sparks(280, 185, is_shield=True)
                                        boss_msg = f"Тотем спас от ошибки! Осталось тотемов: {p['totems']}"
                                        set_next_boss_task()
                                    else:
                                        boss_streak = 0
                                        boss_msg = f"ОШИБКА (было {boss_ans})! Серия ударов сброшена!"
                                        spawn_dust(280, 190, color=(220, 50, 50))
                                        set_next_boss_task()

            elif game_state == "FINAL_STATS":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    error_details = player_data.get("marathon_error_details", [])
                    total_pages = max(1, math.ceil(len(error_details) / STATS_PER_PAGE))
                    if stats_page > 0 and stats_prev_btn.collidepoint(mouse_pos):
                        stats_page -= 1
                    elif stats_page < total_pages - 1 and stats_next_btn.collidepoint(mouse_pos):
                        stats_page += 1
                    elif stats_restart_btn.collidepoint(mouse_pos):
                        reset_entire_marathon()

            elif game_state == "HISTORY":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    history = player_data.get("game_history", [])
                    total_pages = max(1, math.ceil(len(history) / HISTORY_PER_PAGE))
                    if history_back_btn.collidepoint(mouse_pos):
                        game_state = "LOGIN"
                    elif history_page > 0 and history_prev_btn.collidepoint(mouse_pos):
                        history_page -= 1
                    elif history_page < total_pages - 1 and history_next_btn.collidepoint(mouse_pos):
                        history_page += 1
                    else:
                        page_start = history_page * HISTORY_PER_PAGE
                        page_indices = list(range(len(history) - 1, -1, -1))[page_start:page_start + HISTORY_PER_PAGE]
                        for row_idx, record_index in enumerate(page_indices):
                            if history_detail_buttons[row_idx].collidepoint(mouse_pos):
                                history_selected_index = record_index
                                stats_page = 0
                                game_state = "HISTORY_DETAIL"
                                break

            elif game_state == "HISTORY_DETAIL":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    history = player_data.get("game_history", [])
                    if history_back_btn.collidepoint(mouse_pos):
                        game_state = "HISTORY"
                    elif history_selected_index is not None and 0 <= history_selected_index < len(history):
                        details = history[history_selected_index].get("error_details", [])
                        total_pages = max(1, math.ceil(len(details) / STATS_PER_PAGE))
                        if stats_page > 0 and history_prev_btn.collidepoint(mouse_pos):
                            stats_page -= 1
                        elif stats_page < total_pages - 1 and history_next_btn.collidepoint(mouse_pos):
                            stats_page += 1

            elif game_state == "MOB_BATTLE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if mob_hp == 0 or mob_failed_reset:
                        if mob_btn_continue.collidepoint(mouse_pos):
                            if mob_failed_reset:
                                task_num = current_world_idx * STEPS_PER_WORLD + 1
                                step_in_world = 0
                                hero_x = float(platforms[0][0])
                                hero_y = float(platforms[0][1] - 24)
                                target_x, target_y = hero_x, hero_y
                                is_moving = False
                                all_data = load_data()
                                p = all_data[player_name.strip()]
                                p["task_num"] = task_num
                                save_data(all_data)
                                player_data = p
                                question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])
                                message = "Моб победил! Уровень начат заново!"
                                message_color = RED
                                game_state = "GAME"
                            else:
                                all_data = load_data()
                                p = all_data[player_name.strip()]
                                p["emeralds"] += 5
                                save_data(all_data)
                                player_data = p
                                question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])
                                message = "Моб повержен! Путь открыт!"
                                message_color = GREEN
                                game_state = "GAME"
                    else:
                        for i, rect in enumerate(mob_answer_buttons):
                            if rect.collidepoint(mouse_pos):
                                all_data = load_data()
                                p = all_data[player_name.strip()]

                                if mob_choices[i] == mob_ans:
                                    play_sound("hit")
                                    mob_hp -= 1
                                    sword_swing_timer = 12
                                    mob_flash_timer = 10
                                    spawn_hit_sparks(720, 160)

                                    if mob_hp == 0:
                                        mob_battle_result_msg = "ПОБЕДА! Моб повержен! (+5 изумрудов!)"
                                    else:
                                        mob_battle_result_msg = f"Точный удар! Осталось сердец: {mob_hp}"
                                        route_ops = get_route_world(p, current_world_idx)["ops"]
                                        mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(route_ops)
                                else:
                                    play_sound("wrong")
                                    if p.get("totems", 0) > 0:
                                        p["totems"] -= 1
                                        save_data(all_data)
                                        player_data = p
                                        spawn_hit_sparks(280, 185, is_shield=True)
                                        mob_battle_result_msg = f"Тотем спас от сброса биома! (Осталось: {p['totems']})"
                                        route_ops = get_route_world(p, current_world_idx)["ops"]
                                        mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(route_ops)
                                    else:
                                        mob_failed_reset = True
                                        mob_battle_result_msg = f"ОШИБКА! Правильно: {mob_ans}. Уровень сброшен!"
                                        spawn_dust(280, 190, color=(220, 50, 50))

            elif game_state == "REVIEW":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if review_btn_continue.collidepoint(mouse_pos):
                        if len(ten_errors) == 0:
                            all_data = load_data()
                            p = all_data[player_name.strip()]
                            p["emeralds"] += 5
                            save_data(all_data)
                            player_data = p

                        ten_errors = []
                        if task_num > TOTAL_QUESTS:
                            game_state = "GAME"
                        else:
                            current_world_idx = (task_num - 1) // STEPS_PER_WORLD
                            step_in_world = 0
                            hero_x = float(platforms[0][0])
                            hero_y = float(platforms[0][1] - 24)
                            target_x, target_y = hero_x, hero_y
                            is_moving = False
                            question_str, correct_ans, choices, current_op, clean_expr = make_math_task(get_route_world(player_data, current_world_idx)["ops"])
                            message = "Новый биом открыт! Вперёд!"
                            message_color = DARK_TEXT
                            game_state = "GAME"

            elif game_state == "WORKBENCH":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(30, 12, 100, 32).collidepoint(mouse_pos):
                        game_state = "GAME"
                        continue

                    if tab_helmets_rect.collidepoint(mouse_pos): workbench_tab = "HELMETS"
                    elif tab_vehicles_rect.collidepoint(mouse_pos): workbench_tab = "VEHICLES"
                    elif tab_artifacts_rect.collidepoint(mouse_pos): workbench_tab = "ARTIFACTS"
                    elif tab_potions_rect.collidepoint(mouse_pos): workbench_tab = "POTIONS"

                    all_data = load_data()
                    p = all_data[player_name.strip()]

                    if workbench_tab == "HELMETS":
                        for idx, (h_id, h_info) in enumerate(HELMETS.items()):
                            _, _, b_btn = get_shop_row_rects(idx, len(HELMETS))
                            if b_btn.collidepoint(mouse_pos):
                                if h_id in p.get("unlocked_helmets", ["none"]):
                                    current_durability = p.setdefault("helmet_durability", {}).get(
                                        h_id,
                                        h_info.get("max_durability", 0)
                                    )
                                    if h_id == "none" or current_durability > 0:
                                        p["helmet"] = h_id
                                        save_data(all_data)
                                    elif p["emeralds"] >= h_info.get("repair_cost", 0):
                                        p["emeralds"] -= h_info["repair_cost"]
                                        p["helmet_durability"][h_id] = h_info["max_durability"]
                                        p["helmet"] = h_id
                                        play_sound("purchase")
                                        save_data(all_data)
                                elif p["emeralds"] >= h_info["cost"]:
                                    p["emeralds"] -= h_info["cost"]
                                    p["unlocked_helmets"].append(h_id)
                                    p.setdefault("helmet_durability", {})[h_id] = h_info.get("max_durability", 0)
                                    p["helmet"] = h_id
                                    play_sound("purchase")
                                    save_data(all_data)
                                player_data = p

                    elif workbench_tab == "VEHICLES":
                        for idx, w_info in enumerate(WORLDS):
                            _, _, b_upg = get_shop_row_rects(idx, len(WORLDS))
                            if b_upg.collidepoint(mouse_pos):
                                v_code = w_info["vehicle_type"]
                                if v_code not in p["upgraded_vehicles"] and p["emeralds"] >= w_info["upg_cost"]:
                                    p["emeralds"] -= w_info["upg_cost"]
                                    p["upgraded_vehicles"].append(v_code)
                                    play_sound("purchase")
                                    save_data(all_data)
                                player_data = p

                    elif workbench_tab == "ARTIFACTS":
                        for idx, (art_id, art_info) in enumerate(ARTIFACTS.items()):
                            _, _, b_art = get_shop_row_rects(idx, len(ARTIFACTS))
                            if b_art.collidepoint(mouse_pos):
                                if art_id not in p["artifacts"] and p["emeralds"] >= art_info["cost"]:
                                    p["emeralds"] -= art_info["cost"]
                                    p["artifacts"].append(art_id)
                                    play_sound("purchase")
                                    save_data(all_data)
                                player_data = p

                    elif workbench_tab == "POTIONS":
                        for idx, (pot_id, pot_info) in enumerate(POTIONS.items()):
                            _, _, b_pot = get_shop_row_rects(idx, len(POTIONS))
                            if b_pot.collidepoint(mouse_pos):
                                if pot_id == "totem":
                                    if p.get("totems", 0) < pot_info["max"] and p["emeralds"] >= pot_info["cost"]:
                                        p["emeralds"] -= pot_info["cost"]
                                        p["totems"] = p.get("totems", 0) + 1
                                        play_sound("purchase")
                                        save_data(all_data)
                                        player_data = p
                                elif pot_id == "luck":
                                    if p.get("luck_timer", 0) == 0 and p["emeralds"] >= pot_info["cost"]:
                                        p["emeralds"] -= pot_info["cost"]
                                        p["luck_timer"] = 10
                                        play_sound("purchase")
                                        save_data(all_data)
                                        player_data = p

        if squash_val < 1.0:
            squash_val += 0.08
            if squash_val > 1.0: squash_val = 1.0

        cur_w = WORLDS[current_world_idx]
        cur_route = get_route_world(player_data, current_world_idx)
        cur_v_type = cur_w["vehicle_type"]
        is_upgraded = cur_v_type in player_data.get("upgraded_vehicles", []) if player_data else False

        if is_moving:
            move_progress += 0.075
            if anim_tick % 3 == 0:
                spawn_dust(hero_x, hero_y + 20)

            if move_progress >= 1.0:
                move_progress = 1.0
                is_moving = False
                hero_x, hero_y = target_x, target_y
                squash_val = 0.75
                spawn_dust(hero_x, hero_y + 22)

                if task_num > TOTAL_QUESTS:
                    start_boss_battle()
                elif (
                    not player_data.get("sage_completed", False)
                    and player_data.get("sage_task") == task_num - 1
                ):
                    start_sage_encounter()
                elif step_in_world == cur_route.get("mob_step", 5):
                    start_mob_encounter()
                elif (task_num - 1) % STEPS_PER_WORLD == 0 and (task_num - 1) > 0:
                    game_state = "REVIEW"
            else:
                prev_x = platforms[step_in_world - 1][0]
                hero_x = prev_x + (target_x - prev_x) * move_progress

                if cur_v_type in ["pig", "llama"]:
                    hero_y = (platforms[0][1] - 24) - 28 * abs(math.sin(move_progress * math.pi * 2))
                elif cur_v_type == "boat":
                    hero_y = (platforms[0][1] - 24)
                elif cur_v_type == "strider":
                    hero_y = (platforms[0][1] - 24) - 16 * abs(math.sin(move_progress * math.pi * 3))
                elif cur_v_type == "dragon":
                    hero_y = (platforms[0][1] - 24) - 75 * math.sin(move_progress * math.pi)

        if combo_count >= 5 and game_state == "GAME":
            spawn_speed_bubbles(hero_x, hero_y)

        for pt in particles[:]:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[5] -= 1
            if pt[5] <= 0:
                particles.remove(pt)

        for ft in floating_texts[:]:
            ft[2] -= 1.0
            ft[4] -= 1
            if ft[4] <= 0:
                floating_texts.remove(ft)

        # Отрисовка
        if game_state == "LOGIN":
            screen.fill((115, 170, 225))
            card = pygame.Rect(WIDTH // 2 - 320, 75, 640, 360)
            pygame.draw.rect(screen, MC_GUI_BG, card)
            pygame.draw.rect(screen, MC_GUI_LIGHT, (card.left, card.top, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_DARK, (card.left, card.bottom - 3, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_BLACK, card, 3)

            draw_emerald(screen, WIDTH // 2, 115, r=16)
            t1 = FONT_TITLE.render("Математика в Майнкрафте", True, DARK_TEXT)
            t2 = FONT_MED.render("Выбери игрока", True, (70, 80, 100))
            screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 145))
            screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 190))

            for profile_name, profile in PLAYER_PROFILES.items():
                row_y = 255 if profile_name == "Ксения" else 340
                profile_text = FONT_BIG.render(f"{profile_name} · {profile['grade']} класс", True, (35, 55, 95))
                screen.blit(profile_text, (card.x + 35, row_y - profile_text.get_height() // 2 + 10))
                draw_mc_button(
                    screen,
                    player_play_buttons[profile_name],
                    "Играть",
                    player_play_buttons[profile_name].collidepoint(mouse_pos),
                    custom_bg=(60, 140, 70)
                )
                draw_mc_button(
                    screen,
                    player_stats_buttons[profile_name],
                    "Статистика",
                    player_stats_buttons[profile_name].collidepoint(mouse_pos),
                    custom_bg=(75, 105, 155)
                )

        elif game_state == "GAME":
            screen.fill(cur_w["sky"])
            pygame.draw.rect(screen, cur_w["ground"], (0, base_y + 15, WIDTH, HEIGHT - base_y - 15))
            pygame.draw.rect(screen, (40, 30, 20), (0, base_y + 13, WIDTH, 3))

            for i, (px, py) in enumerate(platforms):
                b_rect = pygame.Rect(px - 26, py, 52, 28)
                pygame.draw.rect(screen, cur_w["plat"], b_rect)
                pygame.draw.rect(screen, cur_w["top_plat"], (b_rect.x, b_rect.y, b_rect.width, 7))
                pygame.draw.rect(screen, MC_GUI_BLACK, b_rect, 2)
                
                mob_step = cur_route.get("mob_step", 5)
                if i == mob_step and step_in_world < mob_step:
                    draw_mob(screen, px, py - 35, cur_route["mob_id"], anim_tick=anim_tick)
                sage_task = player_data.get("sage_task")
                sage_step = sage_task - current_world_idx * STEPS_PER_WORLD if sage_task is not None else -1
                if (
                    not player_data.get("sage_completed", False)
                    and i == sage_step
                    and step_in_world < sage_step
                ):
                    draw_sage_fouras(screen, px, py - 42, anim_tick=anim_tick)
                if current_world_idx == 4 and i == 10 and task_num <= TOTAL_QUESTS:
                    pygame.draw.circle(screen, PURPLE, (px, py - 30), 12)
                    pygame.draw.circle(screen, WHITE, (px, py - 30), 4)

                num_lbl = FONT_SMALL.render(str(current_world_idx * 10 + i), True, WHITE if not cur_w["dark_text"] else DARK_TEXT)
                screen.blit(num_lbl, (px - num_lbl.get_width()//2, py + 30))

            for pt in particles:
                pygame.draw.rect(screen, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

            draw_steve_animated(screen, int(hero_x), int(hero_y), cur_v_type, is_upgraded, 
                                helmet=player_data.get("helmet", "none"), 
                                anim_tick=anim_tick, is_moving=is_moving, squash=squash_val, sword_swing=sword_swing_timer)

            for ft in floating_texts:
                f_surf = FONT_BIG.render(ft[0], True, ft[3])
                f_shadow = FONT_BIG.render(ft[0], True, MC_GUI_BLACK)
                screen.blit(f_shadow, (int(ft[1]) - f_surf.get_width()//2 + 1, int(ft[2]) + 1))
                screen.blit(f_surf, (int(ft[1]) - f_surf.get_width()//2, int(ft[2])))

            totems_cnt = player_data.get("totems", 0)
            luck_cnt = player_data.get("luck_timer", 0)
            errors_cnt = player_data.get("marathon_errors", 0)
            equipped_helmet = player_data.get("helmet", "none")
            helmet_durability = player_data.get("helmet_durability", {}).get(equipped_helmet, 0)
            totem_info = f" | Т: {totems_cnt}" if totems_cnt > 0 else ""
            luck_info = f" | Уд: x2 ({luck_cnt})" if luck_cnt > 0 else ""
            errors_info = f" | О: {errors_cnt}" if errors_cnt > 0 else ""
            helmet_info = f" | Ш: {helmet_durability}" if equipped_helmet != "none" else ""

            bar_box = pygame.Rect(15, 10, 360, 34)
            pygame.draw.rect(screen, MC_GUI_BG, bar_box)
            pygame.draw.rect(screen, MC_GUI_LIGHT, (bar_box.left, bar_box.top, bar_box.width, 2))
            pygame.draw.rect(screen, MC_GUI_DARK, (bar_box.left, bar_box.bottom - 2, bar_box.width, 2))
            pygame.draw.rect(screen, MC_GUI_BLACK, bar_box, 2)

            draw_emerald(screen, 32, 27, r=8)
            info_label = f"{player_data['emeralds']}{totem_info}{luck_info}{helmet_info}{errors_info} | {player_name}"
            info_font = FONT_MED if FONT_MED.size(info_label)[0] <= bar_box.width - 40 else FONT_SMALL
            info_txt = info_font.render(info_label, True, DARK_TEXT)
            screen.blit(info_txt, (46, 17))

            draw_mc_button(screen, nav_workbench, "Верстак", nav_workbench.collidepoint(mouse_pos), font_pref=FONT_SMALL)
            draw_mc_button(screen, nav_players, "Игроки", nav_players.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(95, 100, 125))
            sound_label = "Звук: да" if sound_enabled else "Звук: нет"
            draw_mc_button(screen, nav_sound, sound_label, nav_sound.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(70, 115, 155))
            draw_mc_button(screen, nav_reset_game, "Сброс", nav_reset_game.collidepoint(mouse_pos), font_pref=FONT_SMALL, custom_bg=(180, 60, 60))
            draw_mc_button(screen, nav_fullscreen, "Во весь", nav_fullscreen.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(90, 100, 120))

            exp_w = 460
            exp_bg = pygame.Rect(WIDTH//2 - exp_w//2, 54, exp_w, 10)
            pygame.draw.rect(screen, (30, 30, 30), exp_bg)
            fill_w = int(min(task_num - 1, TOTAL_QUESTS) / TOTAL_QUESTS * exp_w)
            pygame.draw.rect(screen, (120, 255, 60), (exp_bg.x, exp_bg.y, fill_w, 10))
            pygame.draw.rect(screen, MC_GUI_BLACK, exp_bg, 2)

            v_title = cur_w["upg_name"] if is_upgraded else cur_w["v_name"]
            title_world = FONT_BIG.render(f"{cur_w['name']}  ({v_title})  [{min(task_num, 50)} / {TOTAL_QUESTS}]", True, DARK_TEXT if cur_w["dark_text"] else WHITE)
            screen.blit(title_world, (WIDTH//2 - title_world.get_width()//2, 72))

            is_treasure_task = task_num in player_data.get("treasure_tasks", [])
            if is_treasure_task and task_num <= TOTAL_QUESTS:
                draw_readable_badge(screen, WIDTH // 2, 118, "ЗАДАНИЕ-СОКРОВИЩЕ: +2 ИЗУМРУДА", border_col=(160, 125, 20), text_col=MC_GOLD, font=FONT_SMALL)
            elif combo_count >= 5:
                draw_readable_badge(screen, WIDTH // 2, 118, f"СЕРИЯ x{combo_count} БЕЗ ОШИБОК! (+2 изумруда)", border_col=(140, 120, 40), text_col=MC_GOLD, font=FONT_SMALL)

            if task_num <= TOTAL_QUESTS:
                q_box = pygame.Rect(WIDTH//2 - 130, 152, 260, 58)
                pygame.draw.rect(screen, (185, 145, 45) if is_treasure_task else (160, 115, 65), q_box)
                pygame.draw.rect(screen, (255, 220, 70) if is_treasure_task else (100, 65, 30), q_box, 3)
                q_txt = FONT_TITLE.render(question_str, True, WHITE)
                screen.blit(q_txt, (q_box.centerx - q_txt.get_width()//2, q_box.centery - q_txt.get_height()//2))

                for i, rect in enumerate(answer_buttons):
                    draw_mc_button(screen, rect, str(choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

                if combo_count >= 5:
                    msg_b_col = (140, 120, 40)
                elif message_color == GREEN:
                    msg_b_col = (50, 140, 65)
                else:
                    msg_b_col = (70, 70, 75)

                draw_readable_badge(screen, WIDTH // 2, 318, message, border_col=msg_b_col, text_col=WHITE, font=FONT_MED)
            else:
                win_box = pygame.Rect(WIDTH//2 - 330, 150, 660, 290)
                pygame.draw.rect(screen, MC_GUI_BG, win_box)
                pygame.draw.rect(screen, MC_GOLD, win_box, 4)
                w1 = FONT_TITLE.render("МАРАФОН 50 ПРОЙДЕН! ДРАКОН СВЕРГНУТ!", True, GREEN)
                w2 = FONT_BIG.render("Ты абсолютный чемпион Математики в Minecraft!", True, DARK_TEXT)
                w3 = FONT_MED.render("Все 50 сложнейших примеров успешно решены!", True, (80, 80, 80))
                screen.blit(w1, (WIDTH//2 - w1.get_width()//2, 180))
                screen.blit(w2, (WIDTH//2 - w2.get_width()//2, 235))
                screen.blit(w3, (WIDTH//2 - w3.get_width()//2, 280))

                draw_mc_button(screen, final_win_restart_btn, "Начать новый марафон", final_win_restart_btn.collidepoint(mouse_pos), font_pref=FONT_MED, custom_bg=(60, 140, 70))

        elif game_state == "CONFIRM_RESET":
            screen.fill((40, 40, 45))
            m_box = pygame.Rect(WIDTH // 2 - 240, 160, 480, 230)
            pygame.draw.rect(screen, MC_GUI_BG, m_box)
            pygame.draw.rect(screen, MC_GUI_BLACK, m_box, 3)

            t_r1 = FONT_TITLE.render("Сбросить марафон сначала?", True, RED)
            t_r2 = FONT_MED.render("Ты вернёшься на 1-й пример 1-го мира.", True, DARK_TEXT)
            t_r3 = FONT_SMALL.render("(Твои изумруды, шлемы, тотемы СОХРАНЯТСЯ)", True, (40, 140, 40))

            screen.blit(t_r1, (WIDTH // 2 - t_r1.get_width() // 2, 190))
            screen.blit(t_r2, (WIDTH // 2 - t_r2.get_width() // 2, 235))
            screen.blit(t_r3, (WIDTH // 2 - t_r3.get_width() // 2, 265))

            draw_mc_button(screen, confirm_reset_yes, "Да, сбросить", confirm_reset_yes.collidepoint(mouse_pos), custom_bg=(210, 60, 60))
            draw_mc_button(screen, confirm_reset_no, "Отмена", confirm_reset_no.collidepoint(mouse_pos), custom_bg=(90, 160, 90))

        elif game_state == "MOB_BATTLE":
            screen.fill((45, 45, 52))
            arena_card = pygame.Rect(120, 20, 760, 560)
            pygame.draw.rect(screen, MC_GUI_BG, arena_card)
            pygame.draw.rect(screen, MC_GUI_BLACK, arena_card, 3)

            mob_name = cur_route["mob_name"]
            t_mob = FONT_TITLE.render(f"БИТВА СО СТРАЖЕМ: {mob_name.upper()}!", True, RED)
            screen.blit(t_mob, (WIDTH // 2 - t_mob.get_width() // 2, 38))

            pygame.draw.rect(screen, (100, 100, 105), (210, 205, 140, 20))
            pygame.draw.rect(screen, (60, 60, 65), (210, 205, 140, 20), 2)
            s_lbl = FONT_SMALL.render(player_name, True, DARK_TEXT)
            screen.blit(s_lbl, (280 - s_lbl.get_width() // 2, 95))
            draw_steve_animated(screen, 280, 175, cur_v_type, is_upgraded,
                                helmet=player_data.get("helmet", "none"),
                                anim_tick=anim_tick, sword_swing=sword_swing_timer)

            vs_box = pygame.Rect(WIDTH // 2 - 24, 150, 48, 32)
            pygame.draw.rect(screen, (220, 60, 60), vs_box, border_radius=6)
            vs_txt = FONT_BIG.render("VS", True, WHITE)
            screen.blit(vs_txt, (vs_box.centerx - vs_txt.get_width() // 2, vs_box.centery - vs_txt.get_height() // 2))

            pygame.draw.rect(screen, (100, 100, 105), (650, 205, 140, 20))
            pygame.draw.rect(screen, (60, 60, 65), (650, 205, 140, 20), 2)
            
            hearts_start_x = 720 - (mob_max_hp * 26) // 2 + 13
            for h_i in range(mob_max_hp):
                draw_mc_heart(screen, hearts_start_x + h_i * 26, 95, filled=(h_i < mob_hp))

            draw_mob(screen, 720, 165, cur_route["mob_id"], anim_tick=anim_tick, flash_red=(mob_flash_timer > 0))

            for pt in particles:
                pygame.draw.rect(screen, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

            if mob_hp > 0 and not mob_failed_reset:
                q_mob_box = pygame.Rect(WIDTH // 2 - 140, 260, 280, 62)
                pygame.draw.rect(screen, (160, 115, 65), q_mob_box)
                pygame.draw.rect(screen, (100, 65, 30), q_mob_box, 3)
                q_txt = FONT_TITLE.render(mob_task_str, True, WHITE)
                screen.blit(q_txt, (q_mob_box.centerx - q_txt.get_width() // 2, q_mob_box.centery - q_txt.get_height() // 2))

                for i, rect in enumerate(mob_answer_buttons):
                    draw_mc_button(screen, rect, str(mob_choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

                draw_readable_badge(screen, WIDTH // 2, 425, mob_battle_result_msg, border_col=(70, 70, 75), text_col=WHITE, font=FONT_MED)

                totem_hint = f"Активных тотемов защиты: {player_data.get('totems', 0)} шт." if player_data.get('totems', 0) > 0 else "Тотемов нет! Ошибка сбросит биом в начало!"
                th_surf = FONT_SMALL.render(totem_hint, True, (40, 130, 40) if player_data.get('totems', 0) > 0 else (160, 60, 60))
                screen.blit(th_surf, (WIDTH // 2 - th_surf.get_width() // 2, 460))
            else:
                res_box = pygame.Rect(WIDTH // 2 - 250, 260, 500, 185)
                pygame.draw.rect(screen, WHITE, res_box, border_radius=8)
                pygame.draw.rect(screen, GREEN if mob_hp == 0 else RED, res_box, 3, border_radius=8)

                r_title = FONT_BIG.render(mob_battle_result_msg, True, GREEN if mob_hp == 0 else RED)
                screen.blit(r_title, (WIDTH // 2 - r_title.get_width() // 2, 290))

                sub_info = "Ты одолел стража биома и добыл трофеи!" if mob_hp == 0 else "Моб нанёс критический удар и отбросил тебя назад..."
                sub_s = FONT_MED.render(sub_info, True, DARK_TEXT)
                screen.blit(sub_s, (WIDTH // 2 - sub_s.get_width() // 2, 345))

                btn_txt = "Продолжить путь!" if mob_hp == 0 else "Попробовать биом сначала"
                draw_mc_button(screen, mob_btn_continue, btn_txt, mob_btn_continue.collidepoint(mouse_pos), font_pref=FONT_MED)

        elif game_state == "SAGE_CHALLENGE":
            screen.fill((25, 32, 48))
            pygame.draw.rect(screen, (70, 75, 90), (0, 430, WIDTH, 170))
            for tower_x in (90, 790):
                pygame.draw.rect(screen, (105, 105, 115), (tower_x, 70, 120, 360))
                for stone_y in range(90, 420, 45):
                    pygame.draw.line(screen, (75, 75, 85), (tower_x, stone_y), (tower_x + 120, stone_y), 2)
                pygame.draw.rect(screen, (45, 45, 55), (tower_x + 38, 130, 44, 80), border_radius=18)

            card = pygame.Rect(210, 25, 580, 535)
            pygame.draw.rect(screen, (198, 198, 198), card)
            pygame.draw.rect(screen, MC_GOLD, card, 4)
            title = FONT_TITLE.render("ИСПЫТАНИЕ СТАРЦА ФУРА", True, (75, 55, 100))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 48))
            draw_sage_fouras(screen, WIDTH // 2, 155, anim_tick)

            if not sage_won:
                draw_centered_wrapped_text(
                    screen, sage_question, FONT_BIG, DARK_TEXT,
                    WIDTH // 2, 225, 520, 5
                )
                for i, rect in enumerate(sage_answer_buttons):
                    draw_mc_button(
                        screen, rect, str(sage_choices[i]), rect.collidepoint(mouse_pos),
                        font_pref=FONT_MED, custom_bg=(90, 75, 125)
                    )
                draw_readable_badge(
                    screen, WIDTH // 2, 455, sage_msg,
                    border_col=MC_GOLD, text_col=WHITE, font=FONT_SMALL
                )
            else:
                reward_box = pygame.Rect(WIDTH // 2 - 250, 245, 500, 150)
                pygame.draw.rect(screen, (245, 235, 190), reward_box, border_radius=8)
                pygame.draw.rect(screen, MC_GOLD, reward_box, 3, border_radius=8)
                reward_title = FONT_TITLE.render("ЗАГАДКА РАЗГАДАНА!", True, GREEN)
                screen.blit(reward_title, (WIDTH // 2 - reward_title.get_width() // 2, 270))
                draw_centered_wrapped_text(
                    screen, f"Старец вручает тебе: {sage_reward_name}", FONT_BIG,
                    (85, 60, 25), WIDTH // 2, 320, 450
                )
                draw_mc_button(
                    screen, sage_continue_btn, "Забрать артефакт и продолжить",
                    sage_continue_btn.collidepoint(mouse_pos), font_pref=FONT_MED,
                    custom_bg=(65, 145, 75)
                )

        elif game_state == "BOSS_BATTLE":
            screen.fill((15, 10, 25))
            arena_card = pygame.Rect(120, 20, 760, 560)
            pygame.draw.rect(screen, (35, 30, 45), arena_card)
            pygame.draw.rect(screen, PURPLE, arena_card, 3)

            bbar_w = 500
            bbar_rect = pygame.Rect(WIDTH // 2 - bbar_w // 2, 38, bbar_w, 14)
            pygame.draw.rect(screen, (20, 15, 30), bbar_rect)
            boss_fill = int((boss_max_hp - boss_streak) / boss_max_hp * bbar_w)
            pygame.draw.rect(screen, (210, 60, 240), (bbar_rect.x, bbar_rect.y, boss_fill, 14))
            pygame.draw.rect(screen, WHITE, bbar_rect, 2)

            t_boss = FONT_TITLE.render("ФИНАЛЬНЫЙ БОСС: ДРАКОН КРАЯ", True, (240, 140, 255))
            screen.blit(t_boss, (WIDTH // 2 - t_boss.get_width() // 2, 58))

            pygame.draw.rect(screen, (50, 45, 60), (210, 215, 140, 18))
            draw_steve_animated(screen, 280, 185, "dragon", True,
                                helmet=player_data.get("helmet", "none"),
                                anim_tick=anim_tick, sword_swing=sword_swing_timer)
            
            if boss_max_hp <= 10:
                hearts_start_x = 720 - (boss_max_hp * 26) // 2 + 13
                for h_i in range(boss_max_hp):
                    draw_mc_heart(screen, hearts_start_x + h_i * 26, 95, filled=(h_i < boss_streak))
            else:
                streak_surf = FONT_MED.render(f"Серия ударов: {boss_streak} / {boss_max_hp}", True, WHITE)
                screen.blit(streak_surf, (720 - streak_surf.get_width() // 2, 87))

            draw_ender_dragon_boss(screen, 720, 175, anim_tick=anim_tick, flash_red=(mob_flash_timer > 0))

            for pt in particles:
                pygame.draw.rect(screen, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

            if not boss_won:
                if boss_is_review:
                    draw_readable_badge(
                        screen, WIDTH // 2, 240, "ПОВТОР ОШИБКИ ИЗ МАРАФОНА",
                        border_col=(210, 80, 80), text_col=(255, 210, 190), font=FONT_SMALL
                    )
                q_boss_box = pygame.Rect(WIDTH // 2 - 140, 260, 280, 62)
                pygame.draw.rect(screen, (160, 115, 65), q_boss_box)
                pygame.draw.rect(screen, (100, 65, 30), q_boss_box, 3)
                q_txt = FONT_TITLE.render(boss_task_str, True, WHITE)
                screen.blit(q_txt, (q_boss_box.centerx - q_txt.get_width() // 2, q_boss_box.centery - q_txt.get_height() // 2))

                for i, rect in enumerate(boss_answer_buttons):
                    draw_mc_button(screen, rect, str(boss_choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

                draw_readable_badge(screen, WIDTH // 2, 425, boss_msg, border_col=(90, 70, 120), text_col=WHITE, font=FONT_MED)

                totem_hint = f"Тотемов для защиты: {player_data.get('totems', 0)} шт."
                th_surf = FONT_SMALL.render(totem_hint, True, (200, 180, 240))
                screen.blit(th_surf, (WIDTH // 2 - th_surf.get_width() // 2, 460))
            else:
                res_box = pygame.Rect(WIDTH // 2 - 250, 250, 500, 195)
                pygame.draw.rect(screen, (40, 35, 50), res_box, border_radius=8)
                pygame.draw.rect(screen, MC_GOLD, res_box, 3, border_radius=8)

                r_title = FONT_TITLE.render("ДРАКОН КРАЯ ПОБЕЖДЁН!", True, GREEN)
                screen.blit(r_title, (WIDTH // 2 - r_title.get_width() // 2, 280))

                sub_info = f"Ты решил все {boss_max_hp} сложнейших примеров подряд!"
                sub_reward = "Супер-награда за победу: +50 ИЗУМРУДОВ!"
                screen.blit(FONT_MED.render(sub_info, True, WHITE), (WIDTH // 2 - FONT_MED.size(sub_info)[0] // 2, 325))
                screen.blit(FONT_BIG.render(sub_reward, True, MC_EMERALD), (WIDTH // 2 - FONT_BIG.size(sub_reward)[0] // 2, 360))

                draw_mc_button(screen, boss_btn_finish, "Посмотреть статистику", boss_btn_finish.collidepoint(mouse_pos), font_pref=FONT_MED)

        elif game_state == "FINAL_STATS":
            screen.fill((28, 32, 42))
            stats_card = pygame.Rect(120, 20, 760, 560)
            pygame.draw.rect(screen, MC_GUI_BG, stats_card)
            pygame.draw.rect(screen, MC_GOLD, stats_card, 4)

            stats_title = FONT_TITLE.render("СТАТИСТИКА МАРАФОНА", True, (35, 115, 65))
            screen.blit(stats_title, (WIDTH // 2 - stats_title.get_width() // 2, 42))

            error_details = player_data.get("marathon_error_details", [])
            total_errors = player_data.get("marathon_errors", len(error_details))
            helmet_saves = player_data.get("helmet_protections", 0)
            summary = FONT_BIG.render(
                f"Ошибок: {total_errors} | Шлем защитил: {helmet_saves} | Серия босса: {boss_max_hp}",
                True,
                DARK_TEXT
            )
            screen.blit(summary, (WIDTH // 2 - summary.get_width() // 2, 82))

            if error_details:
                total_pages = max(1, math.ceil(len(error_details) / STATS_PER_PAGE))
                stats_page = min(stats_page, total_pages - 1)
                page_start = stats_page * STATS_PER_PAGE
                page_errors = error_details[page_start:page_start + STATS_PER_PAGE]

                for row_idx, error in enumerate(page_errors):
                    item_idx = page_start + row_idx + 1
                    row = pygame.Rect(stats_card.x + 35, 120 + row_idx * 56, stats_card.width - 70, 46)
                    pygame.draw.rect(screen, (225, 228, 232), row)
                    pygame.draw.rect(screen, MC_GUI_DARK, row, 2)

                    error_text = (
                        f"{item_idx}. {'[Ш] ' if error.get('protected_by_helmet') else ''}"
                        f"Биом {error.get('world', '?')}, задание {error.get('task', '?')}: "
                        f"{error.get('expr', '?')} = {error.get('wrong', '?')}; верно: {error.get('correct', '?')}"
                    )
                    error_surf = FONT_MED.render(error_text, True, DARK_TEXT)
                    screen.blit(error_surf, (row.x + 12, row.centery - error_surf.get_height() // 2))

                page_label = FONT_SMALL.render(f"Страница {stats_page + 1} из {total_pages}", True, (80, 80, 80))
                screen.blit(page_label, (WIDTH // 2 - page_label.get_width() // 2, 467))

                if stats_page > 0:
                    draw_mc_button(screen, stats_prev_btn, "< Назад", stats_prev_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
                if stats_page < total_pages - 1:
                    draw_mc_button(screen, stats_next_btn, "Дальше >", stats_next_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
            elif total_errors > 0:
                legacy_text = FONT_MED.render("Подробности прежних ошибок не сохранились в старой версии игры.", True, (150, 75, 45))
                screen.blit(legacy_text, (WIDTH // 2 - legacy_text.get_width() // 2, 225))
            else:
                perfect_title = FONT_TITLE.render("ИДЕАЛЬНОЕ ПРОХОЖДЕНИЕ!", True, GREEN)
                perfect_text = FONT_BIG.render("Все задания решены без единой ошибки.", True, DARK_TEXT)
                screen.blit(perfect_title, (WIDTH // 2 - perfect_title.get_width() // 2, 195))
                screen.blit(perfect_text, (WIDTH // 2 - perfect_text.get_width() // 2, 250))

            draw_mc_button(screen, stats_restart_btn, "Новый марафон", stats_restart_btn.collidepoint(mouse_pos), font_pref=FONT_MED, custom_bg=(60, 140, 70))

        elif game_state == "HISTORY":
            screen.fill((35, 40, 52))
            history_card = pygame.Rect(120, 20, 760, 560)
            pygame.draw.rect(screen, MC_GUI_BG, history_card)
            pygame.draw.rect(screen, (70, 105, 165), history_card, 4)

            history_title = FONT_TITLE.render(f"ИСТОРИЯ ИГР — {player_name.upper()}", True, (35, 75, 145))
            screen.blit(history_title, (WIDTH // 2 - history_title.get_width() // 2, 42))

            history = player_data.get("game_history", [])
            if history:
                total_errors_all = sum(record.get("errors", 0) for record in history)
                average_errors = total_errors_all / len(history)
                history_summary = FONT_MED.render(
                    f"Завершено игр: {len(history)} | Всего ошибок: {total_errors_all} | В среднем: {average_errors:.1f}",
                    True,
                    DARK_TEXT
                )
                screen.blit(history_summary, (WIDTH // 2 - history_summary.get_width() // 2, 82))

                total_pages = max(1, math.ceil(len(history) / HISTORY_PER_PAGE))
                history_page = min(history_page, total_pages - 1)
                page_start = history_page * HISTORY_PER_PAGE
                page_indices = list(range(len(history) - 1, -1, -1))[page_start:page_start + HISTORY_PER_PAGE]

                for row_idx, record_index in enumerate(page_indices):
                    record = history[record_index]
                    row = pygame.Rect(history_card.x + 35, 115 + row_idx * 72, history_card.width - 70, 58)
                    pygame.draw.rect(screen, (225, 228, 235), row)
                    pygame.draw.rect(screen, (80, 95, 125), row, 2)

                    completed_at = str(record.get("completed_at", "Дата неизвестна")).replace("T", " ")
                    row_title = FONT_MED.render(f"Игра #{record_index + 1} · {completed_at}", True, DARK_TEXT)
                    row_info = FONT_SMALL.render(
                        f"Ошибок: {record.get('errors', 0)} · Шлем защитил: {record.get('helmet_protections', 0)} · Босс: {record.get('boss_hp', 5)}",
                        True,
                        (75, 75, 85)
                    )
                    screen.blit(row_title, (row.x + 12, row.y + 7))
                    screen.blit(row_info, (row.x + 12, row.y + 32))
                    draw_mc_button(
                        screen,
                        history_detail_buttons[row_idx],
                        "Подробнее",
                        history_detail_buttons[row_idx].collidepoint(mouse_pos),
                        font_pref=FONT_SMALL,
                        custom_bg=(75, 105, 155)
                    )

                page_label = FONT_SMALL.render(f"Страница {history_page + 1} из {total_pages}", True, (80, 80, 80))
                screen.blit(page_label, (WIDTH // 2 - page_label.get_width() // 2, 482))

                if history_page > 0:
                    draw_mc_button(screen, history_prev_btn, "< Назад", history_prev_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
                if history_page < total_pages - 1:
                    draw_mc_button(screen, history_next_btn, "Дальше >", history_next_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
            else:
                empty_title = FONT_TITLE.render("Завершённых игр пока нет", True, (80, 90, 110))
                empty_hint = FONT_MED.render("История появится после победы над Драконом.", True, (90, 90, 95))
                screen.blit(empty_title, (WIDTH // 2 - empty_title.get_width() // 2, 220))
                screen.blit(empty_hint, (WIDTH // 2 - empty_hint.get_width() // 2, 270))

            draw_mc_button(screen, history_back_btn, "К игрокам", history_back_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)

        elif game_state == "HISTORY_DETAIL":
            screen.fill((35, 40, 52))
            detail_card = pygame.Rect(120, 20, 760, 560)
            pygame.draw.rect(screen, MC_GUI_BG, detail_card)
            pygame.draw.rect(screen, (70, 105, 165), detail_card, 4)

            history = player_data.get("game_history", [])
            record = history[history_selected_index] if history_selected_index is not None and 0 <= history_selected_index < len(history) else {}
            detail_title = FONT_TITLE.render(f"{player_name.upper()} · ИГРА #{(history_selected_index or 0) + 1}", True, (35, 75, 145))
            screen.blit(detail_title, (WIDTH // 2 - detail_title.get_width() // 2, 42))

            completed_at = str(record.get("completed_at", "Дата неизвестна")).replace("T", " ")
            detail_summary = FONT_MED.render(
                f"{completed_at} | Ошибок: {record.get('errors', 0)} | Шлем: {record.get('helmet_protections', 0)} | Босс: {record.get('boss_hp', 5)}",
                True,
                DARK_TEXT
            )
            screen.blit(detail_summary, (WIDTH // 2 - detail_summary.get_width() // 2, 82))

            details = record.get("error_details", [])
            if details:
                total_pages = max(1, math.ceil(len(details) / STATS_PER_PAGE))
                stats_page = min(stats_page, total_pages - 1)
                page_start = stats_page * STATS_PER_PAGE
                for row_idx, error in enumerate(details[page_start:page_start + STATS_PER_PAGE]):
                    item_idx = page_start + row_idx + 1
                    row = pygame.Rect(detail_card.x + 35, 120 + row_idx * 56, detail_card.width - 70, 46)
                    pygame.draw.rect(screen, (225, 228, 232), row)
                    pygame.draw.rect(screen, MC_GUI_DARK, row, 2)
                    error_text = (
                        f"{item_idx}. {'[Ш] ' if error.get('protected_by_helmet') else ''}"
                        f"Биом {error.get('world', '?')}, задание {error.get('task', '?')}: "
                        f"{error.get('expr', '?')} = {error.get('wrong', '?')}; верно: {error.get('correct', '?')}"
                    )
                    error_surf = FONT_MED.render(error_text, True, DARK_TEXT)
                    screen.blit(error_surf, (row.x + 12, row.centery - error_surf.get_height() // 2))

                page_label = FONT_SMALL.render(f"Страница {stats_page + 1} из {total_pages}", True, (80, 80, 80))
                screen.blit(page_label, (WIDTH // 2 - page_label.get_width() // 2, 467))
                if stats_page > 0:
                    draw_mc_button(screen, history_prev_btn, "< Назад", history_prev_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
                if stats_page < total_pages - 1:
                    draw_mc_button(screen, history_next_btn, "Дальше >", history_next_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
            else:
                perfect_title = FONT_TITLE.render("ИГРА БЕЗ ОШИБОК!", True, GREEN)
                screen.blit(perfect_title, (WIDTH // 2 - perfect_title.get_width() // 2, 230))

            draw_mc_button(screen, history_back_btn, "К истории", history_back_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)

        elif game_state == "REVIEW":
            screen.fill((50, 50, 55))
            card = pygame.Rect(WIDTH // 2 - 320, 25, 640, 540)
            pygame.draw.rect(screen, MC_GUI_BG, card)
            pygame.draw.rect(screen, MC_GUI_LIGHT, (card.left, card.top, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_DARK, (card.left, card.bottom - 3, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_BLACK, card, 3)

            fin_world_idx = ((task_num - 2) // STEPS_PER_WORLD)
            w_title = WORLDS[fin_world_idx]["name"]

            t_head = FONT_TITLE.render(f"Итоги биома: {w_title}", True, DARK_TEXT)
            screen.blit(t_head, (WIDTH // 2 - t_head.get_width() // 2, 45))

            if len(ten_errors) > 0:
                total_errors = player_data.get("marathon_errors", 0)
                sub = FONT_MED.render(f"Ошибки биома: {len(ten_errors)}. Всего в марафоне: {total_errors}.", True, (160, 30, 30))
                screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 85))

                for idx, err in enumerate(ten_errors[:6]):
                    y_pos = 130 + idx * 54
                    r_box = pygame.Rect(card.x + 35, y_pos, card.width - 70, 46)
                    pygame.draw.rect(screen, (220, 220, 220), r_box)
                    pygame.draw.rect(screen, MC_GUI_DARK, r_box, 2)

                    ex_surf = FONT_BIG.render(f"{err['expr']} =", True, DARK_TEXT)
                    screen.blit(ex_surf, (r_box.x + 20, r_box.centery - ex_surf.get_height() // 2))

                    w_tag = FONT_MED.render(f"Твой ответ: {err['wrong']} (ошибка)", True, RED)
                    screen.blit(w_tag, (r_box.x + 160, r_box.centery - w_tag.get_height() // 2))

                    c_tag = FONT_BIG.render(f"Верно: {err['correct']}", True, GREEN)
                    screen.blit(c_tag, (r_box.right - c_tag.get_width() - 20, r_box.centery - c_tag.get_height() // 2))

                btn_txt = "Все понятно, в следующий биом!"
            else:
                draw_emerald(screen, WIDTH // 2, 165, r=26)
                c1 = FONT_TITLE.render("ИДЕАЛЬНО! ЧИСТЫЙ КРАФТ!", True, GREEN)
                c2 = FONT_MED.render("Ты прошёл весь биом без единой ошибки!", True, DARK_TEXT)
                c3 = FONT_BIG.render("Бонус жителя деревни: +5 Изумрудов!", True, (0, 140, 50))

                screen.blit(c1, (WIDTH // 2 - c1.get_width() // 2, 220))
                screen.blit(c2, (WIDTH // 2 - c2.get_width() // 2, 270))
                screen.blit(c3, (WIDTH // 2 - c3.get_width() // 2, 320))

                btn_txt = "В следующий биом!"

            draw_mc_button(screen, review_btn_continue, btn_txt, review_btn_continue.collidepoint(mouse_pos), font_pref=FONT_MED)

        elif game_state == "WORKBENCH":
            screen.fill((45, 45, 50))
            draw_mc_button(screen, pygame.Rect(30, 12, 100, 32), "<< В мир", pygame.Rect(30, 12, 100, 32).collidepoint(mouse_pos), font_pref=FONT_SMALL)

            title = FONT_TITLE.render("Верстак и Алхимическая Стойка", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 15))
            b_count = FONT_BIG.render(f"Изумруды: {player_data['emeralds']}", True, (100, 255, 120))
            screen.blit(b_count, (WIDTH - b_count.get_width() - 40, 18))

            draw_mc_button(screen, tab_helmets_rect, "Шлемы", tab_helmets_rect.collidepoint(mouse_pos), 
                           custom_bg=(170, 170, 175) if workbench_tab == "HELMETS" else (90, 90, 95))
            draw_mc_button(screen, tab_vehicles_rect, "Транспорт", tab_vehicles_rect.collidepoint(mouse_pos), 
                           custom_bg=(170, 170, 175) if workbench_tab == "VEHICLES" else (90, 90, 95))
            draw_mc_button(screen, tab_artifacts_rect, "Оружие", tab_artifacts_rect.collidepoint(mouse_pos), 
                           custom_bg=(170, 170, 175) if workbench_tab == "ARTIFACTS" else (90, 90, 95))
            draw_mc_button(screen, tab_potions_rect, "Зелья и Тотемы", tab_potions_rect.collidepoint(mouse_pos), 
                           custom_bg=(170, 170, 175) if workbench_tab == "POTIONS" else (90, 90, 95))

            pygame.draw.rect(screen, MC_GUI_BG, content_box)
            pygame.draw.rect(screen, MC_GUI_BLACK, content_box, 3)

            if workbench_tab == "HELMETS":
                for idx, (h_id, h_info) in enumerate(HELMETS.items()):
                    row_rect, slot_rect, b_btn = get_shop_row_rects(idx, len(HELMETS))
                    pygame.draw.rect(screen, (220, 220, 220), row_rect)
                    pygame.draw.rect(screen, MC_GUI_DARK, row_rect, 1)

                    draw_mc_slot_frame(screen, slot_rect.x, slot_rect.y, 50)
                    draw_item_icon(screen, f"helm_{h_id}", slot_rect.centerx, slot_rect.centery)

                    screen.blit(FONT_MED.render(h_info["name"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 10))

                    is_unlocked = h_id in player_data.get("unlocked_helmets", ["none"])
                    is_equipped = player_data.get("helmet") == h_id
                    current_durability = player_data.get("helmet_durability", {}).get(
                        h_id,
                        h_info.get("max_durability", 0)
                    )

                    if h_id == "none":
                        helmet_status = "Бесплатно"
                    elif not is_unlocked:
                        helmet_status = f"Цена: {h_info['cost']} · прочность: {h_info['max_durability']}"
                    elif current_durability <= 0:
                        helmet_status = f"Сломан · ремонт: {h_info['repair_cost']} изумр."
                    else:
                        helmet_status = f"Прочность: {current_durability} из {h_info['max_durability']}"
                    screen.blit(FONT_SMALL.render(helmet_status, True, (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 34))

                    if is_equipped:
                        draw_mc_button(screen, b_btn, "Надето", False, False, font_pref=FONT_SMALL)
                    elif is_unlocked and current_durability <= 0 and h_id != "none":
                        can_repair = player_data["emeralds"] >= h_info["repair_cost"]
                        draw_mc_button(screen, b_btn, f"Ремонт {h_info['repair_cost']}", b_btn.collidepoint(mouse_pos) and can_repair, can_repair, font_pref=FONT_SMALL)
                    elif is_unlocked:
                        draw_mc_button(screen, b_btn, "Надеть", b_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
                    else:
                        can = player_data["emeralds"] >= h_info["cost"]
                        draw_mc_button(screen, b_btn, "Купить", b_btn.collidepoint(mouse_pos) and can, can, font_pref=FONT_SMALL)

            elif workbench_tab == "VEHICLES":
                for idx, w_info in enumerate(WORLDS):
                    row_rect, slot_rect, b_upg = get_shop_row_rects(idx, len(WORLDS))
                    pygame.draw.rect(screen, (220, 220, 220), row_rect)
                    pygame.draw.rect(screen, MC_GUI_DARK, row_rect, 1)

                    draw_mc_slot_frame(screen, slot_rect.x, slot_rect.y, 50)
                    draw_item_icon(screen, f"veh_{w_info['vehicle_type']}", slot_rect.centerx, slot_rect.centery)

                    screen.blit(FONT_MED.render(f"{w_info['v_name']} -> {w_info['upg_name']}", True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 10))
                    screen.blit(FONT_SMALL.render(f"Цена улучшения: {w_info['upg_cost']} изумрудов", True, (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 34))

                    is_upg = w_info["vehicle_type"] in player_data.get("upgraded_vehicles", [])

                    if is_upg:
                        draw_mc_button(screen, b_upg, "Готово!", False, False, font_pref=FONT_SMALL)
                    else:
                        can_u = player_data["emeralds"] >= w_info["upg_cost"]
                        draw_mc_button(screen, b_upg, "Прокачать", b_upg.collidepoint(mouse_pos) and can_u, can_u, font_pref=FONT_SMALL)

            elif workbench_tab == "ARTIFACTS":
                for idx, (art_id, art_info) in enumerate(ARTIFACTS.items()):
                    row_rect, slot_rect, b_art = get_shop_row_rects(idx, len(ARTIFACTS))
                    pygame.draw.rect(screen, (225, 230, 240), row_rect)
                    pygame.draw.rect(screen, (70, 90, 140), row_rect, 2)

                    draw_mc_slot_frame(screen, slot_rect.x, slot_rect.y, 50)
                    draw_item_icon(screen, art_id, slot_rect.centerx, slot_rect.centery)

                    screen.blit(FONT_BIG.render(art_info["name"], True, (30, 60, 140)), (slot_rect.right + 15, row_rect.y + 6))
                    screen.blit(FONT_SMALL.render(art_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                    screen.blit(FONT_TINY.render(f"Цена: {art_info['cost']} изумрудов", True, (0, 130, 40)), (slot_rect.right + 15, row_rect.y + 44))

                    is_bought = art_id in player_data.get("artifacts", [])

                    if is_bought:
                        draw_mc_button(screen, b_art, "Активен!", False, False, font_pref=FONT_SMALL, custom_bg=(60, 140, 70))
                    else:
                        can_b = player_data["emeralds"] >= art_info["cost"]
                        draw_mc_button(screen, b_art, "Купить", b_art.collidepoint(mouse_pos) and can_b, can_b, font_pref=FONT_SMALL)

            elif workbench_tab == "POTIONS":
                for idx, (pot_id, pot_info) in enumerate(POTIONS.items()):
                    row_rect, slot_rect, b_pot = get_shop_row_rects(idx, len(POTIONS))
                    pygame.draw.rect(screen, (245, 235, 250), row_rect)
                    pygame.draw.rect(screen, PURPLE, row_rect, 2)

                    draw_mc_slot_frame(screen, slot_rect.x, slot_rect.y, 50)
                    draw_item_icon(screen, pot_id, slot_rect.centerx, slot_rect.centery)

                    cnt = player_data.get("totems", 0) if pot_id == "totem" else (1 if player_data.get("luck_timer", 0) > 0 else 0)
                    screen.blit(FONT_BIG.render(f"{pot_info['name']} (В наличии: {cnt} из {pot_info['max']})", True, PURPLE), (slot_rect.right + 15, row_rect.y + 6))
                    screen.blit(FONT_SMALL.render(pot_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                    screen.blit(FONT_TINY.render(f"Цена: {pot_info['cost']} изумрудов", True, (0, 130, 40)), (slot_rect.right + 15, row_rect.y + 44))

                    is_full = cnt >= pot_info["max"]

                    if is_full:
                        draw_mc_button(screen, b_pot, "Максимум", False, False, font_pref=FONT_SMALL, custom_bg=(110, 110, 115))
                    else:
                        can_buy = player_data["emeralds"] >= pot_info["cost"]
                        draw_mc_button(screen, b_pot, "Купить", b_pot.collidepoint(mouse_pos) and can_buy, can_buy, font_pref=FONT_SMALL, custom_bg=(130, 60, 170))

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

# Запуск игры
asyncio.run(main())
