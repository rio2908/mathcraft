import pygame
import random
import sys
import math
import json
import os
from datetime import date, datetime

# 1. Инициализация Pygame
pygame.init()
pygame.font.init()

# Виртуальный холст игры
V_WIDTH, V_HEIGHT = 1000, 600
canvas = pygame.Surface((V_WIDTH, V_HEIGHT))

# 2. Безопасное определение экрана для Android
disp_info = pygame.display.Info()
REAL_WIDTH = disp_info.current_w if disp_info.current_w > 0 else V_WIDTH
REAL_HEIGHT = disp_info.current_h if disp_info.current_h > 0 else V_HEIGHT

screen = pygame.display.set_mode((REAL_WIDTH, REAL_HEIGHT))
pygame.display.set_caption("MathCraft")
clock = pygame.time.Clock()

# 3. Безопасные встроенные шрифты (без вызова системного match_font)
def get_safe_font(size):
    return pygame.font.Font(None, size)

FONT_TITLE = get_safe_font(28)
FONT_BIG = get_safe_font(23)
FONT_MED = get_safe_font(19)
FONT_SMALL = get_safe_font(16)
FONT_TINY = get_safe_font(13)

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
    {"name": "1. Равнины Обычного Мира", "sky": (140, 205, 255), "ground": (85, 140, 50), "plat": (115, 80, 50), "top_plat": (105, 175, 55), "dark_text": True, "ops": ["+", "-"], "vehicle_type": "pig", "v_name": "Свинка", "upg_name": "Бронированная свинка", "upg_cost": 15, "mob_id": "creeper", "mob_name": "Крипер"},
    {"name": "2. Жаркая Пустыня", "sky": (245, 215, 160), "ground": (210, 165, 85), "plat": (180, 130, 60), "top_plat": (225, 185, 100), "dark_text": True, "ops": ["-", "+"], "vehicle_type": "llama", "v_name": "Лама", "upg_name": "Боевая Лама в попоне", "upg_cost": 20, "mob_id": "skeleton", "mob_name": "Скелет с луком"},
    {"name": "3. Ледяные Равнины", "sky": (195, 225, 245), "ground": (220, 235, 245), "plat": (140, 190, 230), "top_plat": (175, 220, 255), "dark_text": True, "ops": ["*"], "vehicle_type": "boat", "v_name": "Лодка на льду", "upg_name": "Лодка с сундуком", "upg_cost": 25, "mob_id": "stray", "mob_name": "Зимогор"},
    {"name": "4. Незер (Нижний Мир)", "sky": (65, 15, 15), "ground": (90, 20, 20), "plat": (50, 10, 10), "top_plat": (240, 90, 20), "dark_text": False, "ops": ["/"], "vehicle_type": "strider", "v_name": "Страйдер по лаве", "upg_name": "Страйдер в седле", "upg_cost": 30, "mob_id": "blaze", "mob_name": "Ифрит Незера"},
    {"name": "5. Эндер Мир (Край)", "sky": (15, 10, 25), "ground": (30, 25, 45), "plat": (50, 45, 70), "top_plat": (230, 230, 175), "dark_text": False, "ops": ["+", "-", "*", "/"], "vehicle_type": "dragon", "v_name": "Элитры", "upg_name": "Дракон Края", "upg_cost": 40, "mob_id": "enderman", "mob_name": "Эндермен"}
]

HELMETS = {
    "none": {"name": "Без шлема", "cost": 0},
    "leather": {"name": "Кожаный шлем", "cost": 10, "color": (160, 90, 45)},
    "iron": {"name": "Железный шлем", "cost": 15, "color": (210, 210, 215)},
    "diamond": {"name": "Алмазный шлем", "cost": 25, "color": (45, 225, 220)},
    "netherite": {"name": "Незеритовый шлем", "cost": 35, "color": (65, 55, 65)}
}

ARTIFACTS = {
    "sharp_sword": {"name": "Меч «Острота»", "desc": "Мобы биомов: нужно всего 2 примера!", "cost": 20},
    "strength_potion": {"name": "Зелье Силы II", "desc": "Мобы биомов: победа с 1 примера (ваншот)!", "cost": 35},
    "dragon_bow": {"name": "Лук Силы", "desc": "Дракон Края: нужно 4 примера (вместо 5)!", "cost": 30},
    "end_crystal": {"name": "Кристалл Края", "desc": "Дракон Края: нужно всего 3 примера!", "cost": 45}
}

POTIONS = {
    "totem": {"name": "Тотем Бессмертия", "desc": "Спасает от 1 ошибки в бою со стражем или Драконом!", "cost": 15, "max": 3},
    "luck": {"name": "Зелье Удачи", "desc": "Даёт удвоенные изумруды на следующие 10 примеров!", "cost": 20, "max": 1}
}

# Внутренняя память приложения
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_PATH, "mc_math_save.json")
LAST_PLAYER_FILE = os.path.join(BASE_PATH, "mc_last_player.txt")

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

def get_player(name):
    profiles = load_data()
    name = name.strip()
    today_str = date.today().isoformat()
    if name not in profiles:
        profiles[name] = {
            "emeralds": 10, "streak": 1, "last_date": today_str,
            "task_num": 1, "helmet": "none", "unlocked_helmets": ["none"],
            "upgraded_vehicles": [], "artifacts": [], "totems": 1, "luck_timer": 0
        }
    else:
        p = profiles[name]
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

    save_data(profiles)
    set_last_player(name)
    return profiles[name]

def get_mob_max_hp():
    arts = player_data.get("artifacts", []) if player_data else []
    if "strength_potion" in arts: return 1
    if "sharp_sword" in arts: return 2
    return 3

def get_boss_max_hp():
    arts = player_data.get("artifacts", []) if player_data else []
    if "end_crystal" in arts: return 3
    if "dragon_bow" in arts: return 4
    return 5

def make_math_task(ops_list):
    op = random.choice(ops_list)
    if op == "+":
        ans = random.randint(5, 20)
        a = random.randint(2, ans - 2)
        b = ans - a
        sym = "+"
    elif op == "-":
        a = random.randint(6, 20)
        b = random.randint(2, a - 2)
        ans = a - b
        sym = "-"
    elif op == "*":
        pairs = [(x, y) for x in range(2, 11) for y in range(2, 11) if x * y <= 20]
        a, b = random.choice(pairs)
        ans = a * b
        sym = "x"
    else:
        div_pairs = []
        for d in range(2, 11):
            for res in range(2, (20 // d) + 1):
                div_pairs.append((d * res, d, res))
        a, b, ans = random.choice(div_pairs)
        sym = ":"

    variants = {ans}
    while len(variants) < 3:
        fake = ans + random.choice([-3, -2, -1, 1, 2, 3])
        if 1 <= fake <= 20 and fake != ans:
            variants.add(fake)
            
    v_list = list(variants)
    random.shuffle(v_list)
    return f"{a} {sym} {b} = ?", ans, v_list, op, f"{a} {sym} {b}"

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

TOTAL_QUESTS = 50
STEPS_PER_WORLD = 10
base_y = 490
platforms = [(95 + i * ((WIDTH - 190) // STEPS_PER_WORLD), base_y) for i in range(STEPS_PER_WORLD + 1)]

last_saved_name = get_last_player()
if last_saved_name:
    player_name = last_saved_name
    player_data = get_player(player_name)
    game_state = "GAME"
else:
    player_name = ""
    player_data = None
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
question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
message = "Добудь правильный ответ!"
message_color = DARK_TEXT

mob_max_hp = 3
mob_hp = 3
mob_task_str = ""
mob_ans = 0
mob_choices = []
mob_clean_expr = ""
mob_op = "+"
mob_battle_result_msg = ""
mob_failed_reset = False

boss_max_hp = 5
boss_streak = 0
boss_task_str = ""
boss_ans = 0
boss_choices = []
boss_op = "+"
boss_clean_expr = ""
boss_msg = "Победи Дракона!"
boss_won = False

workbench_tab = "HELMETS"

btn_w, btn_h = 140, 54
start_btn_x = (WIDTH - (3 * btn_w + 40)) // 2
answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 235, btn_w, btn_h) for i in range(3)]
mob_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]
boss_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]

nav_workbench = pygame.Rect(WIDTH - 380, 10, 125, 34)
nav_switch_player = pygame.Rect(WIDTH - 245, 10, 125, 34)
nav_reset_game = pygame.Rect(WIDTH - 110, 10, 95, 34)

confirm_reset_yes = pygame.Rect(WIDTH // 2 - 130, 310, 110, 42)
confirm_reset_no = pygame.Rect(WIDTH // 2 + 20, 310, 110, 42)

mob_btn_continue = pygame.Rect(WIDTH // 2 - 145, 475, 290, 48)
boss_btn_finish = pygame.Rect(WIDTH // 2 - 150, 475, 300, 48)
review_btn_continue = pygame.Rect(WIDTH // 2 - 160, 500, 320, 48)
final_win_restart_btn = pygame.Rect(WIDTH // 2 - 140, 385, 280, 46)

tab_helmets_rect = pygame.Rect(140, 55, 170, 36)
tab_vehicles_rect = pygame.Rect(325, 55, 175, 36)
tab_artifacts_rect = pygame.Rect(515, 55, 175, 36)
tab_potions_rect = pygame.Rect(705, 55, 175, 36)

def start_mob_encounter():
    global game_state, mob_hp, mob_max_hp, mob_task_str, mob_ans, mob_choices, mob_clean_expr, mob_op, mob_battle_result_msg, mob_failed_reset
    game_state = "MOB_BATTLE"
    mob_max_hp = get_mob_max_hp()
    mob_hp = mob_max_hp
    mob_failed_reset = False
    mob_battle_result_msg = f"Реши пример, чтобы нанести удар!"
    mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(["+", "-", "*", "/"])

def start_boss_battle():
    global game_state, boss_streak, boss_max_hp, boss_task_str, boss_ans, boss_choices, boss_clean_expr, boss_op, boss_msg, boss_won
    game_state = "BOSS_BATTLE"
    boss_max_hp = get_boss_max_hp()
    boss_streak = 0
    boss_won = False
    boss_msg = f"Реши {boss_max_hp} примеров подряд, чтобы одолеть Дракона!"
    boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_math_task(["+", "-", "*", "/"])

def reset_entire_marathon():
    global task_num, step_in_world, current_world_idx, hero_x, hero_y, target_x, target_y, is_moving, ten_errors, question_str, correct_ans, choices, current_op, clean_expr, game_state, message, message_color
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
        save_data(all_data)
        
    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[0]["ops"])
    message = "Марафон начат сначала! Вперёд!"
    message_color = DARK_TEXT
    game_state = "GAME"

pygame.key.start_text_input()
running = True

while running:
    anim_tick += 1
    
    scale = min(REAL_WIDTH / V_WIDTH, REAL_HEIGHT / V_HEIGHT)
    offset_x = (REAL_WIDTH - int(V_WIDTH * scale)) // 2
    offset_y = (REAL_HEIGHT - int(V_HEIGHT * scale)) // 2
    
    real_mouse_pos = pygame.mouse.get_pos()
    mouse_pos = (
        int((real_mouse_pos[0] - offset_x) / scale),
        int((real_mouse_pos[1] - offset_y) / scale)
    )

    if sword_swing_timer > 0: sword_swing_timer -= 1
    if mob_flash_timer > 0: mob_flash_timer -= 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif game_state == "LOGIN":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif event.key == pygame.K_RETURN and player_name.strip():
                    player_data = get_player(player_name)
                    task_num = player_data.get("task_num", 1)
                    current_world_idx = min((task_num - 1) // STEPS_PER_WORLD, 4)
                    step_in_world = (task_num - 1) % STEPS_PER_WORLD
                    hero_x = float(platforms[step_in_world][0])
                    hero_y = float(platforms[step_in_world][1] - 24)
                    target_x, target_y = hero_x, hero_y
                    ten_errors = []
                    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
                    game_state = "GAME"
            elif event.type == pygame.TEXTINPUT:
                if len(player_name) < 14:
                    player_name += event.text
            elif event.type == pygame.MOUSEBUTTONDOWN:
                btn_start = pygame.Rect(WIDTH//2 - 100, 330, 200, 46)
                if btn_start.collidepoint(mouse_pos) and player_name.strip():
                    player_data = get_player(player_name)
                    task_num = player_data.get("task_num", 1)
                    current_world_idx = min((task_num - 1) // STEPS_PER_WORLD, 4)
                    step_in_world = (task_num - 1) % STEPS_PER_WORLD
                    hero_x = float(platforms[step_in_world][0])
                    hero_y = float(platforms[step_in_world][1] - 24)
                    target_x, target_y = hero_x, hero_y
                    ten_errors = []
                    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
                    game_state = "GAME"

        elif game_state == "GAME":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if nav_workbench.collidepoint(mouse_pos):
                    game_state = "WORKBENCH"
                    continue
                if nav_switch_player.collidepoint(mouse_pos):
                    player_name = ""
                    game_state = "LOGIN"
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
                                combo_count += 1
                                gain = 2 if combo_count >= 5 else 1
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

                                if combo_count >= 5:
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
                                    question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])

                            else:
                                wrong_val = choices[i]
                                if not any(err["expr"] == clean_expr for err in ten_errors):
                                    ten_errors.append({
                                        "expr": clean_expr,
                                        "wrong": wrong_val,
                                        "correct": correct_ans
                                    })
                                combo_count = 0
                                message = "Ой, крипер взорвал ответ! Попробуй другой!"
                                message_color = RED
                                spawn_dust(hero_x, hero_y, color=(80, 80, 80))

        elif game_state == "CONFIRM_RESET":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if confirm_reset_yes.collidepoint(mouse_pos):
                    reset_entire_marathon()
                elif confirm_reset_no.collidepoint(mouse_pos):
                    game_state = "GAME"

        elif game_state == "BOSS_BATTLE":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if boss_won:
                    if boss_btn_finish.collidepoint(mouse_pos):
                        game_state = "GAME"
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
                                    boss_won = True
                                    boss_msg = "ДРАКОН КРАЯ ПОВЕРЖЕН!"
                                    p["emeralds"] += 50
                                    save_data(all_data)
                                    player_data = p
                                else:
                                    boss_msg = f"Точный удар! Серия: {boss_streak} из {boss_max_hp}!"
                                    boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_math_task(["+", "-", "*", "/"])
                            else:
                                if p.get("totems", 0) > 0:
                                    p["totems"] -= 1
                                    save_data(all_data)
                                    player_data = p
                                    spawn_hit_sparks(280, 185, is_shield=True)
                                    boss_msg = f"Тотем спас от ошибки! Осталось тотемов: {p['totems']}"
                                    boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_math_task(["+", "-", "*", "/"])
                                else:
                                    boss_streak = max(0, boss_streak - 2)
                                    boss_msg = f"ОШИБКА (было {boss_ans})! Откат на 2 шага назад!"
                                    spawn_dust(280, 190, color=(220, 50, 50))
                                    boss_task_str, boss_ans, boss_choices, boss_op, boss_clean_expr = make_math_task(["+", "-", "*", "/"])

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
                            question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
                            message = "Моб победил! Уровень начат заново!"
                            message_color = RED
                            game_state = "GAME"
                        else:
                            all_data = load_data()
                            p = all_data[player_name.strip()]
                            p["emeralds"] += 5
                            save_data(all_data)
                            player_data = p
                            question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
                            message = "Моб повержен! Путь открыт!"
                            message_color = GREEN
                            game_state = "GAME"
                else:
                    for i, rect in enumerate(mob_answer_buttons):
                        if rect.collidepoint(mouse_pos):
                            all_data = load_data()
                            p = all_data[player_name.strip()]

                            if mob_choices[i] == mob_ans:
                                mob_hp -= 1
                                sword_swing_timer = 12
                                mob_flash_timer = 10
                                spawn_hit_sparks(720, 160)

                                if mob_hp == 0:
                                    mob_battle_result_msg = "ПОБЕДА! Моб повержен! (+5 изумрудов!)"
                                else:
                                    mob_battle_result_msg = f"Точный удар! Осталось сердец: {mob_hp}"
                                    mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(["+", "-", "*", "/"])
                            else:
                                if p.get("totems", 0) > 0:
                                    p["totems"] -= 1
                                    save_data(all_data)
                                    player_data = p
                                    spawn_hit_sparks(280, 185, is_shield=True)
                                    mob_battle_result_msg = f"Тотем спас от сброса биома! (Осталось: {p['totems']})"
                                    mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_math_task(["+", "-", "*", "/"])
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
                        question_str, correct_ans, choices, current_op, clean_expr = make_math_task(WORLDS[current_world_idx]["ops"])
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
                                p["helmet"] = h_id
                            elif p["emeralds"] >= h_info["cost"]:
                                p["emeralds"] -= h_info["cost"]
                                p["unlocked_helmets"].append(h_id)
                                p["helmet"] = h_id
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
                                save_data(all_data)
                                player_data = p

                elif workbench_tab == "ARTIFACTS":
                    for idx, (art_id, art_info) in enumerate(ARTIFACTS.items()):
                        _, _, b_art = get_shop_row_rects(idx, len(ARTIFACTS))
                        if b_art.collidepoint(mouse_pos):
                            if art_id not in p["artifacts"] and p["emeralds"] >= art_info["cost"]:
                                p["emeralds"] -= art_info["cost"]
                                p["artifacts"].append(art_id)
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
                                    save_data(all_data)
                                    player_data = p
                            elif pot_id == "luck":
                                if p.get("luck_timer", 0) == 0 and p["emeralds"] >= pot_info["cost"]:
                                    p["emeralds"] -= pot_info["cost"]
                                    p["luck_timer"] = 10
                                    save_data(all_data)
                                    player_data = p

    # --- ОБНОВЛЕНИЕ ФИЗИКИ ---
    if squash_val < 1.0:
        squash_val += 0.08
        if squash_val > 1.0: squash_val = 1.0

    cur_w = WORLDS[current_world_idx]
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
            elif step_in_world == 5:
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

    # ==================== ОТРИСОВКА НА ВИРТУАЛЬНЫЙ ХОЛСТ ====================

    if game_state == "LOGIN":
        canvas.fill((115, 170, 225))
        card = pygame.Rect(V_WIDTH//2 - 240, 100, 480, 330)
        pygame.draw.rect(canvas, MC_GUI_BG, card)
        pygame.draw.rect(canvas, MC_GUI_LIGHT, (card.left, card.top, card.width, 3))
        pygame.draw.rect(canvas, MC_GUI_DARK, (card.left, card.bottom - 3, card.width, 3))
        pygame.draw.rect(canvas, MC_GUI_BLACK, card, 3)

        draw_emerald(canvas, V_WIDTH//2, 145, r=16)
        t1 = FONT_TITLE.render("Математика в Майнкрафте", True, DARK_TEXT)
        t2 = FONT_MED.render("Введи ник игрока для входа:", True, (80, 80, 80))
        canvas.blit(t1, (V_WIDTH//2 - t1.get_width()//2, 175))
        canvas.blit(t2, (V_WIDTH//2 - t2.get_width()//2, 215))

        inp_box = pygame.Rect(V_WIDTH//2 - 150, 255, 300, 42)
        pygame.draw.rect(canvas, (0, 0, 0), inp_box)
        pygame.draw.rect(canvas, (160, 160, 160), inp_box, 2)
        n_surf = FONT_BIG.render(player_name or "Ник...", True, WHITE if player_name else (130, 130, 130))
        canvas.blit(n_surf, (inp_box.x + 10, inp_box.centery - n_surf.get_height()//2))

        btn_start = pygame.Rect(V_WIDTH//2 - 100, 325, 200, 44)
        draw_mc_button(canvas, btn_start, "Играть в мире", btn_start.collidepoint(mouse_pos), bool(player_name.strip()))

    elif game_state == "GAME":
        canvas.fill(cur_w["sky"])

        pygame.draw.rect(canvas, cur_w["ground"], (0, base_y + 15, V_WIDTH, V_HEIGHT - base_y - 15))
        pygame.draw.rect(canvas, (40, 30, 20), (0, base_y + 13, V_WIDTH, 3))

        for i, (px, py) in enumerate(platforms):
            b_rect = pygame.Rect(px - 26, py, 52, 28)
            pygame.draw.rect(canvas, cur_w["plat"], b_rect)
            pygame.draw.rect(canvas, cur_w["top_plat"], (b_rect.x, b_rect.y, b_rect.width, 7))
            pygame.draw.rect(canvas, MC_GUI_BLACK, b_rect, 2)
            
            if i == 5 and step_in_world < 5:
                draw_mob(canvas, px, py - 35, cur_w["mob_id"], anim_tick=anim_tick)
            if current_world_idx == 4 and i == 10 and task_num <= TOTAL_QUESTS:
                pygame.draw.circle(canvas, PURPLE, (px, py - 30), 12)
                pygame.draw.circle(canvas, WHITE, (px, py - 30), 4)

            num_lbl = FONT_SMALL.render(str(current_world_idx * 10 + i), True, WHITE if not cur_w["dark_text"] else DARK_TEXT)
            canvas.blit(num_lbl, (px - num_lbl.get_width()//2, py + 30))

        for pt in particles:
            pygame.draw.rect(canvas, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

        draw_steve_animated(canvas, int(hero_x), int(hero_y), cur_v_type, is_upgraded, 
                            helmet=player_data.get("helmet", "none"), 
                            anim_tick=anim_tick, is_moving=is_moving, squash=squash_val, sword_swing=sword_swing_timer)

        for ft in floating_texts:
            f_surf = FONT_BIG.render(ft[0], True, ft[3])
            f_shadow = FONT_BIG.render(ft[0], True, MC_GUI_BLACK)
            canvas.blit(f_shadow, (int(ft[1]) - f_surf.get_width()//2 + 1, int(ft[2]) + 1))
            canvas.blit(f_surf, (int(ft[1]) - f_surf.get_width()//2, int(ft[2])))

        totems_cnt = player_data.get("totems", 0)
        luck_cnt = player_data.get("luck_timer", 0)
        totem_info = f" | Тотемы: {totems_cnt}" if totems_cnt > 0 else ""
        luck_info = f" | Удача: x2 ({luck_cnt})" if luck_cnt > 0 else ""

        bar_box = pygame.Rect(15, 10, 390, 34)
        pygame.draw.rect(canvas, MC_GUI_BG, bar_box)
        pygame.draw.rect(canvas, MC_GUI_LIGHT, (bar_box.left, bar_box.top, bar_box.width, 2))
        pygame.draw.rect(canvas, MC_GUI_DARK, (bar_box.left, bar_box.bottom - 2, bar_box.width, 2))
        pygame.draw.rect(canvas, MC_GUI_BLACK, bar_box, 2)

        draw_emerald(canvas, 32, 27, r=8)
        info_txt = FONT_MED.render(f"{player_data['emeralds']}{totem_info}{luck_info} | {player_name}", True, DARK_TEXT)
        canvas.blit(info_txt, (46, 17))

        draw_mc_button(canvas, nav_workbench, "Верстак", nav_workbench.collidepoint(mouse_pos), font_pref=FONT_SMALL)
        draw_mc_button(canvas, nav_switch_player, "Игрок", nav_switch_player.collidepoint(mouse_pos), font_pref=FONT_SMALL)
        draw_mc_button(canvas, nav_reset_game, "Сброс", nav_reset_game.collidepoint(mouse_pos), font_pref=FONT_SMALL, custom_bg=(180, 60, 60))

        exp_w = 460
        exp_bg = pygame.Rect(V_WIDTH//2 - exp_w//2, 54, exp_w, 10)
        pygame.draw.rect(canvas, (30, 30, 30), exp_bg)
        fill_w = int(min(task_num - 1, TOTAL_QUESTS) / TOTAL_QUESTS * exp_w)
        pygame.draw.rect(canvas, (120, 255, 60), (exp_bg.x, exp_bg.y, fill_w, 10))
        pygame.draw.rect(canvas, MC_GUI_BLACK, exp_bg, 2)

        v_title = cur_w["upg_name"] if is_upgraded else cur_w["v_name"]
        title_world = FONT_BIG.render(f"{cur_w['name']}  ({v_title})  [{min(task_num, 50)} / {TOTAL_QUESTS}]", True, DARK_TEXT if cur_w["dark_text"] else WHITE)
        canvas.blit(title_world, (V_WIDTH//2 - title_world.get_width()//2, 72))

        if combo_count >= 5:
            draw_readable_badge(canvas, V_WIDTH // 2, 118, f"СЕРИЯ x{combo_count} БЕЗ ОШИБОК! (+2 изумруда)", border_col=(140, 120, 40), text_col=MC_GOLD, font=FONT_SMALL)

        if task_num <= TOTAL_QUESTS:
            q_box = pygame.Rect(V_WIDTH//2 - 130, 152, 260, 58)
            pygame.draw.rect(canvas, (160, 115, 65), q_box)
            pygame.draw.rect(canvas, (100, 65, 30), q_box, 3)
            q_txt = FONT_TITLE.render(question_str, True, WHITE)
            canvas.blit(q_txt, (q_box.centerx - q_txt.get_width()//2, q_box.centery - q_txt.get_height()//2))

            for i, rect in enumerate(answer_buttons):
                draw_mc_button(canvas, rect, str(choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

            if combo_count >= 5:
                msg_b_col = (140, 120, 40)
            elif message_color == GREEN:
                msg_b_col = (50, 140, 65)
            else:
                msg_b_col = (70, 70, 75)

            draw_readable_badge(canvas, V_WIDTH // 2, 318, message, border_col=msg_b_col, text_col=WHITE, font=FONT_MED)
        else:
            win_box = pygame.Rect(V_WIDTH//2 - 280, 150, 560, 290)
            pygame.draw.rect(canvas, MC_GUI_BG, win_box)
            pygame.draw.rect(canvas, MC_GOLD, win_box, 4)
            w1 = FONT_TITLE.render("МАРАФОН 50 ПРОЙДЕН! ДРАКОН СВЕРГНУТ!", True, GREEN)
            w2 = FONT_BIG.render("Ты абсолютный чемпион Математики в Minecraft!", True, DARK_TEXT)
            w3 = FONT_MED.render("Все 50 сложнейших примеров успешно решены!", True, (80, 80, 80))
            canvas.blit(w1, (V_WIDTH//2 - w1.get_width()//2, 180))
            canvas.blit(w2, (V_WIDTH//2 - w2.get_width()//2, 235))
            canvas.blit(w3, (V_WIDTH//2 - w3.get_width()//2, 280))

            draw_mc_button(canvas, final_win_restart_btn, "Начать новый марафон ↺", final_win_restart_btn.collidepoint(mouse_pos), font_pref=FONT_MED, custom_bg=(60, 140, 70))

    elif game_state == "CONFIRM_RESET":
        canvas.fill((40, 40, 45))
        m_box = pygame.Rect(V_WIDTH // 2 - 240, 160, 480, 230)
        pygame.draw.rect(canvas, MC_GUI_BG, m_box)
        pygame.draw.rect(canvas, MC_GUI_BLACK, m_box, 3)

        t_r1 = FONT_TITLE.render("Сбросить марафон сначала?", True, RED)
        t_r2 = FONT_MED.render("Ты вернёшься на 1-й пример 1-го мира.", True, DARK_TEXT)
        t_r3 = FONT_SMALL.render("(Твои изумруды, шлемы, тотемы СОХРАНЯТСЯ)", True, (40, 140, 40))

        canvas.blit(t_r1, (V_WIDTH // 2 - t_r1.get_width() // 2, 190))
        canvas.blit(t_r2, (V_WIDTH // 2 - t_r2.get_width() // 2, 235))
        canvas.blit(t_r3, (V_WIDTH // 2 - t_r3.get_width() // 2, 265))

        draw_mc_button(canvas, confirm_reset_yes, "Да, сбросить", confirm_reset_yes.collidepoint(mouse_pos), custom_bg=(210, 60, 60))
        draw_mc_button(canvas, confirm_reset_no, "Отмена", confirm_reset_no.collidepoint(mouse_pos), custom_bg=(90, 160, 90))

    # --- АРЕНА МОБА ---
    elif game_state == "MOB_BATTLE":
        canvas.fill((45, 45, 52))
        arena_card = pygame.Rect(120, 20, 760, 560)
        pygame.draw.rect(canvas, MC_GUI_BG, arena_card)
        pygame.draw.rect(canvas, MC_GUI_BLACK, arena_card, 3)

        mob_name = cur_w["mob_name"]
        t_mob = FONT_TITLE.render(f"БИТВА СО СТРАЖЕМ: {mob_name.upper()}!", True, RED)
        canvas.blit(t_mob, (V_WIDTH // 2 - t_mob.get_width() // 2, 38))

        pygame.draw.rect(canvas, (100, 100, 105), (210, 205, 140, 20))
        pygame.draw.rect(canvas, (60, 60, 65), (210, 205, 140, 20), 2)
        s_lbl = FONT_SMALL.render(player_name, True, DARK_TEXT)
        canvas.blit(s_lbl, (280 - s_lbl.get_width() // 2, 95))
        draw_steve_animated(canvas, 280, 175, cur_v_type, is_upgraded,
                            helmet=player_data.get("helmet", "none"),
                            anim_tick=anim_tick, sword_swing=sword_swing_timer)

        vs_box = pygame.Rect(V_WIDTH // 2 - 24, 150, 48, 32)
        pygame.draw.rect(canvas, (220, 60, 60), vs_box, border_radius=6)
        vs_txt = FONT_BIG.render("VS", True, WHITE)
        canvas.blit(vs_txt, (vs_box.centerx - vs_txt.get_width() // 2, vs_box.centery - vs_txt.get_height() // 2))

        pygame.draw.rect(canvas, (100, 100, 105), (650, 205, 140, 20))
        pygame.draw.rect(canvas, (60, 60, 65), (650, 205, 140, 20), 2)
        
        hearts_start_x = 720 - (mob_max_hp * 26) // 2 + 13
        for h_i in range(mob_max_hp):
            draw_mc_heart(canvas, hearts_start_x + h_i * 26, 95, filled=(h_i < mob_hp))

        draw_mob(canvas, 720, 165, cur_w["mob_id"], anim_tick=anim_tick, flash_red=(mob_flash_timer > 0))

        for pt in particles:
            pygame.draw.rect(canvas, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

        if mob_hp > 0 and not mob_failed_reset:
            q_mob_box = pygame.Rect(V_WIDTH // 2 - 140, 260, 280, 62)
            pygame.draw.rect(canvas, (160, 115, 65), q_mob_box)
            pygame.draw.rect(canvas, (100, 65, 30), q_mob_box, 3)
            q_txt = FONT_TITLE.render(mob_task_str, True, WHITE)
            canvas.blit(q_txt, (q_mob_box.centerx - q_txt.get_width() // 2, q_mob_box.centery - q_txt.get_height() // 2))

            for i, rect in enumerate(mob_answer_buttons):
                draw_mc_button(canvas, rect, str(mob_choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

            draw_readable_badge(canvas, V_WIDTH // 2, 425, mob_battle_result_msg, border_col=(70, 70, 75), text_col=WHITE, font=FONT_MED)

            totem_hint = f"Активных тотемов защиты: {player_data.get('totems', 0)} шт." if player_data.get('totems', 0) > 0 else "Тотемов нет! Ошибка сбросит биом в начало!"
            th_surf = FONT_SMALL.render(totem_hint, True, (40, 130, 40) if player_data.get('totems', 0) > 0 else (160, 60, 60))
            canvas.blit(th_surf, (V_WIDTH // 2 - th_surf.get_width() // 2, 460))
        else:
            res_box = pygame.Rect(V_WIDTH // 2 - 250, 260, 500, 185)
            pygame.draw.rect(canvas, WHITE, res_box, border_radius=8)
            pygame.draw.rect(canvas, GREEN if mob_hp == 0 else RED, res_box, 3, border_radius=8)

            r_title = FONT_BIG.render(mob_battle_result_msg, True, GREEN if mob_hp == 0 else RED)
            canvas.blit(r_title, (V_WIDTH // 2 - r_title.get_width() // 2, 290))

            sub_info = "Ты одолел стража биома и добыл трофеи!" if mob_hp == 0 else "Моб нанёс критический удар и отбросил тебя назад..."
            sub_s = FONT_MED.render(sub_info, True, DARK_TEXT)
            canvas.blit(sub_s, (V_WIDTH // 2 - sub_s.get_width() // 2, 345))

            btn_txt = "Продолжить путь!" if mob_hp == 0 else "Попробовать биом сначала"
            draw_mc_button(canvas, mob_btn_continue, btn_txt, mob_btn_continue.collidepoint(mouse_pos), font_pref=FONT_MED)

    # --- АРЕНА ДРАКОНА КРАЯ ---
    elif game_state == "BOSS_BATTLE":
        canvas.fill((15, 10, 25))
        arena_card = pygame.Rect(120, 20, 760, 560)
        pygame.draw.rect(canvas, (35, 30, 45), arena_card)
        pygame.draw.rect(canvas, PURPLE, arena_card, 3)

        bbar_w = 500
        bbar_rect = pygame.Rect(V_WIDTH // 2 - bbar_w // 2, 38, bbar_w, 14)
        pygame.draw.rect(canvas, (20, 15, 30), bbar_rect)
        boss_fill = int((boss_max_hp - boss_streak) / boss_max_hp * bbar_w)
        pygame.draw.rect(canvas, (210, 60, 240), (bbar_rect.x, bbar_rect.y, boss_fill, 14))
        pygame.draw.rect(canvas, WHITE, bbar_rect, 2)

        t_boss = FONT_TITLE.render(f"ФИНАЛЬНЫЙ БОСС: ДРАКОН КРАЯ", True, (240, 140, 255))
        canvas.blit(t_boss, (V_WIDTH // 2 - t_boss.get_width() // 2, 58))

        pygame.draw.rect(canvas, (50, 45, 60), (210, 215, 140, 18))
        draw_steve_animated(canvas, 280, 185, "dragon", True,
                            helmet=player_data.get("helmet", "none"),
                            anim_tick=anim_tick, sword_swing=sword_swing_timer)
        
        hearts_start_x = 720 - (boss_max_hp * 26) // 2 + 13
        for h_i in range(boss_max_hp):
            draw_mc_heart(canvas, hearts_start_x + h_i * 26, 95, filled=(h_i < boss_streak))

        draw_ender_dragon_boss(canvas, 720, 175, anim_tick=anim_tick, flash_red=(mob_flash_timer > 0))

        for pt in particles:
            pygame.draw.rect(canvas, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

        if not boss_won:
            q_boss_box = pygame.Rect(V_WIDTH // 2 - 140, 260, 280, 62)
            pygame.draw.rect(canvas, (160, 115, 65), q_boss_box)
            pygame.draw.rect(canvas, (100, 65, 30), q_boss_box, 3)
            q_txt = FONT_TITLE.render(boss_task_str, True, WHITE)
            canvas.blit(q_txt, (q_boss_box.centerx - q_txt.get_width() // 2, q_boss_box.centery - q_txt.get_height() // 2))

            for i, rect in enumerate(boss_answer_buttons):
                draw_mc_button(canvas, rect, str(boss_choices[i]), rect.collidepoint(mouse_pos), font_pref=FONT_BIG)

            draw_readable_badge(canvas, V_WIDTH // 2, 425, boss_msg, border_col=(90, 70, 120), text_col=WHITE, font=FONT_MED)

            totem_hint = f"Тотемов для защиты: {player_data.get('totems', 0)} шт."
            th_surf = FONT_SMALL.render(totem_hint, True, (200, 180, 240))
            canvas.blit(th_surf, (V_WIDTH // 2 - th_surf.get_width() // 2, 460))
        else:
            res_box = pygame.Rect(V_WIDTH // 2 - 250, 250, 500, 195)
            pygame.draw.rect(canvas, (40, 35, 50), res_box, border_radius=8)
            pygame.draw.rect(canvas, MC_GOLD, res_box, 3, border_radius=8)

            r_title = FONT_TITLE.render("ДРАКОН КРАЯ ПОБЕЖДЁН!", True, GREEN)
            canvas.blit(r_title, (V_WIDTH // 2 - r_title.get_width() // 2, 280))

            sub_info = f"Ты решил все {boss_max_hp} сложнейших примеров подряд!"
            sub_reward = "Супер-награда за победу: +50 ИЗУМРУДОВ!"
            canvas.blit(FONT_MED.render(sub_info, True, WHITE), (V_WIDTH // 2 - FONT_MED.size(sub_info)[0] // 2, 325))
            canvas.blit(FONT_BIG.render(sub_reward, True, MC_EMERALD), (V_WIDTH // 2 - FONT_BIG.size(sub_reward)[0] // 2, 360))

            draw_mc_button(canvas, boss_btn_finish, "Завершить Марафон!", boss_btn_finish.collidepoint(mouse_pos), font_pref=FONT_MED)

    elif game_state == "REVIEW":
        canvas.fill((50, 50, 55))
        card = pygame.Rect(V_WIDTH // 2 - 320, 25, 640, 540)
        pygame.draw.rect(canvas, MC_GUI_BG, card)
        pygame.draw.rect(canvas, MC_GUI_LIGHT, (card.left, card.top, card.width, 3))
        pygame.draw.rect(canvas, MC_GUI_DARK, (card.left, card.bottom - 3, card.width, 3))
        pygame.draw.rect(canvas, MC_GUI_BLACK, card, 3)

        fin_world_idx = ((task_num - 2) // STEPS_PER_WORLD)
        w_title = WORLDS[fin_world_idx]["name"]

        t_head = FONT_TITLE.render(f"Итоги биома: {w_title}", True, DARK_TEXT)
        canvas.blit(t_head, (V_WIDTH // 2 - t_head.get_width() // 2, 45))

        if len(ten_errors) > 0:
            sub = FONT_MED.render(f"Неудачные попытки: {len(ten_errors)}. Давай закрепим рецепты!", True, (160, 30, 30))
            canvas.blit(sub, (V_WIDTH // 2 - sub.get_width() // 2, 85))

            for idx, err in enumerate(ten_errors[:6]):
                y_pos = 130 + idx * 54
                r_box = pygame.Rect(card.x + 35, y_pos, card.width - 70, 46)
                pygame.draw.rect(canvas, (220, 220, 220), r_box)
                pygame.draw.rect(canvas, MC_GUI_DARK, r_box, 2)

                ex_surf = FONT_BIG.render(f"{err['expr']} =", True, DARK_TEXT)
                canvas.blit(ex_surf, (r_box.x + 20, r_box.centery - ex_surf.get_height() // 2))

                w_tag = FONT_MED.render(f"Твой ответ: {err['wrong']} (ошибка)", True, RED)
                canvas.blit(w_tag, (r_box.x + 160, r_box.centery - w_tag.get_height() // 2))

                c_tag = FONT_BIG.render(f"Верно: {err['correct']}", True, GREEN)
                canvas.blit(c_tag, (r_box.right - c_tag.get_width() - 20, r_box.centery - c_tag.get_height() // 2))

            btn_txt = "Все понятно, в следующий биом!"
        else:
            draw_emerald(canvas, V_WIDTH // 2, 165, r=26)
            c1 = FONT_TITLE.render("ИДЕАЛЬНО! ЧИСТЫЙ КРАФТ!", True, GREEN)
            c2 = FONT_MED.render("Ты прошёл весь биом без единой ошибки!", True, DARK_TEXT)
            c3 = FONT_BIG.render("Бонус жителя деревни: +5 Изумрудов!", True, (0, 140, 50))

            canvas.blit(c1, (V_WIDTH // 2 - c1.get_width() // 2, 220))
            canvas.blit(c2, (V_WIDTH // 2 - c2.get_width() // 2, 270))
            canvas.blit(c3, (V_WIDTH // 2 - c3.get_width() // 2, 320))

            btn_txt = "В следующий биом!"

        draw_mc_button(canvas, review_btn_continue, btn_txt, review_btn_continue.collidepoint(mouse_pos), font_pref=FONT_MED)

    # --- ВЕРСТАК ---
    elif game_state == "WORKBENCH":
        canvas.fill((45, 45, 50))
        draw_mc_button(canvas, pygame.Rect(30, 12, 100, 32), "<< В мир", pygame.Rect(30, 12, 100, 32).collidepoint(mouse_pos), font_pref=FONT_SMALL)

        title = FONT_TITLE.render("Верстак и Алхимическая Стойка", True, WHITE)
        canvas.blit(title, (V_WIDTH//2 - title.get_width()//2, 15))
        b_count = FONT_BIG.render(f"Изумруды: {player_data['emeralds']}", True, (100, 255, 120))
        canvas.blit(b_count, (V_WIDTH - b_count.get_width() - 40, 18))

        draw_mc_button(canvas, tab_helmets_rect, "Шлемы", tab_helmets_rect.collidepoint(mouse_pos), 
                       custom_bg=(170, 170, 175) if workbench_tab == "HELMETS" else (90, 90, 95))
        draw_mc_button(canvas, tab_vehicles_rect, "Транспорт", tab_vehicles_rect.collidepoint(mouse_pos), 
                       custom_bg=(170, 170, 175) if workbench_tab == "VEHICLES" else (90, 90, 95))
        draw_mc_button(canvas, tab_artifacts_rect, "Оружие", tab_artifacts_rect.collidepoint(mouse_pos), 
                       custom_bg=(170, 170, 175) if workbench_tab == "ARTIFACTS" else (90, 90, 95))
        draw_mc_button(canvas, tab_potions_rect, "Зелья и Тотемы", tab_potions_rect.collidepoint(mouse_pos), 
                       custom_bg=(170, 170, 175) if workbench_tab == "POTIONS" else (90, 90, 95))

        pygame.draw.rect(canvas, MC_GUI_BG, content_box)
        pygame.draw.rect(canvas, MC_GUI_BLACK, content_box, 3)

        if workbench_tab == "HELMETS":
            for idx, (h_id, h_info) in enumerate(HELMETS.items()):
                row_rect, slot_rect, b_btn = get_shop_row_rects(idx, len(HELMETS))
                pygame.draw.rect(canvas, (220, 220, 220), row_rect)
                pygame.draw.rect(canvas, MC_GUI_DARK, row_rect, 1)

                draw_mc_slot_frame(canvas, slot_rect.x, slot_rect.y, 50)
                draw_item_icon(canvas, f"helm_{h_id}", slot_rect.centerx, slot_rect.centery)

                canvas.blit(FONT_MED.render(h_info["name"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 10))
                canvas.blit(FONT_SMALL.render(f"Цена: {h_info['cost']} изумр." if h_info["cost"] > 0 else "Бесплатно", True, (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 34))

                is_unlocked = h_id in player_data.get("unlocked_helmets", ["none"])
                is_equipped = player_data.get("helmet") == h_id

                if is_equipped:
                    draw_mc_button(canvas, b_btn, "Надето", False, False, font_pref=FONT_SMALL)
                elif is_unlocked:
                    draw_mc_button(canvas, b_btn, "Надеть", b_btn.collidepoint(mouse_pos), font_pref=FONT_SMALL)
                else:
                    can = player_data["emeralds"] >= h_info["cost"]
                    draw_mc_button(canvas, b_btn, "Купить", b_btn.collidepoint(mouse_pos) and can, can, font_pref=FONT_SMALL)

        elif workbench_tab == "VEHICLES":
            for idx, w_info in enumerate(WORLDS):
                row_rect, slot_rect, b_upg = get_shop_row_rects(idx, len(WORLDS))
                pygame.draw.rect(canvas, (220, 220, 220), row_rect)
                pygame.draw.rect(canvas, MC_GUI_DARK, row_rect, 1)

                draw_mc_slot_frame(canvas, slot_rect.x, slot_rect.y, 50)
                draw_item_icon(canvas, f"veh_{w_info['vehicle_type']}", slot_rect.centerx, slot_rect.centery)

                canvas.blit(FONT_MED.render(f"{w_info['v_name']} -> {w_info['upg_name']}", True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 10))
                canvas.blit(FONT_SMALL.render(f"Цена улучшения: {w_info['upg_cost']} изумрудов", True, (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 34))

                is_upg = w_info["vehicle_type"] in player_data.get("upgraded_vehicles", [])

                if is_upg:
                    draw_mc_button(canvas, b_upg, "Готово!", False, False, font_pref=FONT_SMALL)
                else:
                    can_u = player_data["emeralds"] >= w_info["upg_cost"]
                    draw_mc_button(canvas, b_upg, "Прокачать", b_upg.collidepoint(mouse_pos) and can_u, can_u, font_pref=FONT_SMALL)

        elif workbench_tab == "ARTIFACTS":
            for idx, (art_id, art_info) in enumerate(ARTIFACTS.items()):
                row_rect, slot_rect, b_art = get_shop_row_rects(idx, len(ARTIFACTS))
                pygame.draw.rect(canvas, (225, 230, 240), row_rect)
                pygame.draw.rect(canvas, (70, 90, 140), row_rect, 2)

                draw_mc_slot_frame(canvas, slot_rect.x, slot_rect.y, 50)
                draw_item_icon(canvas, art_id, slot_rect.centerx, slot_rect.centery)

                canvas.blit(FONT_BIG.render(art_info["name"], True, (30, 60, 140)), (slot_rect.right + 15, row_rect.y + 6))
                canvas.blit(FONT_SMALL.render(art_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                canvas.blit(FONT_TINY.render(f"Цена: {art_info['cost']} изумрудов", True, (0, 130, 40)), (slot_rect.right + 15, row_rect.y + 44))

                is_bought = art_id in player_data.get("artifacts", [])

                if is_bought:
                    draw_mc_button(canvas, b_art, "Активен!", False, False, font_pref=FONT_SMALL, custom_bg=(60, 140, 70))
                else:
                    can_b = player_data["emeralds"] >= art_info["cost"]
                    draw_mc_button(canvas, b_art, "Купить", b_art.collidepoint(mouse_pos) and can_b, can_b, font_pref=FONT_SMALL)

        elif workbench_tab == "POTIONS":
            for idx, (pot_id, pot_info) in enumerate(POTIONS.items()):
                row_rect, slot_rect, b_pot = get_shop_row_rects(idx, len(POTIONS))
                pygame.draw.rect(canvas, (245, 235, 250), row_rect)
                pygame.draw.rect(canvas, PURPLE, row_rect, 2)

                draw_mc_slot_frame(canvas, slot_rect.x, slot_rect.y, 50)
                draw_item_icon(canvas, pot_id, slot_rect.centerx, slot_rect.centery)

                cnt = player_data.get("totems", 0) if pot_id == "totem" else (1 if player_data.get("luck_timer", 0) > 0 else 0)
                canvas.blit(FONT_BIG.render(f"{pot_info['name']} (В наличии: {cnt} из {pot_info['max']})", True, PURPLE), (slot_rect.right + 15, row_rect.y + 6))
                canvas.blit(FONT_SMALL.render(pot_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                canvas.blit(FONT_TINY.render(f"Цена: {pot_info['cost']} изумрудов", True, (0, 130, 40)), (slot_rect.right + 15, row_rect.y + 44))

                is_full = cnt >= pot_info["max"]

                if is_full:
                    draw_mc_button(canvas, b_pot, "Максимум", False, False, font_pref=FONT_SMALL, custom_bg=(110, 110, 115))
                else:
                    can_buy = player_data["emeralds"] >= pot_info["cost"]
                    draw_mc_button(canvas, b_pot, "Купить", b_pot.collidepoint(mouse_pos) and can_buy, can_buy, font_pref=FONT_SMALL, custom_bg=(130, 60, 170))

    # Масштабирование на реальный экран мобильного
    screen.fill((0, 0, 0))
    scaled_surf = pygame.transform.smoothscale(canvas, (int(V_WIDTH * scale), int(V_HEIGHT * scale)))
    screen.blit(scaled_surf, (offset_x, offset_y))

    pygame.display.flip()
    clock.tick(60)

pygame.key.stop_text_input()
pygame.quit()
sys.exit()