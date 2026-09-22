import pygame
import random
import sys
import math
import os
import asyncio
from array import array
from datetime import date, datetime

from game_content import (
    ARTIFACTS,
    HELMETS,
    HELP_PAGES,
    MOB_ABILITIES,
    MOB_POOLS,
    PETS,
    PLAYER_PROFILES,
    POTIONS,
    STEPS_PER_WORLD,
    TOTAL_QUESTS,
    WORLDS,
)
from game_storage import get_last_player, load_data, save_data, set_last_player
from game_tasks import (
    create_adaptive_tasks,
    create_marathon_route,
    create_sage_task,
    create_treasure_tasks,
    get_route_world,
    make_math_task as generate_math_task,
    make_review_task,
    pick_logic_task,
)

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


def request_browser_fullscreen():
    if sys.platform == "emscripten":
        try:
            import platform
            doc = platform.window.document
            if not doc.fullscreenElement:
                doc.documentElement.requestFullscreen()
        except Exception:
            pass


def get_player(name, apply_daily_bonus=True, remember_player=True):
    profiles = load_data()
    name = name.strip()
    today_str = date.today().isoformat()
    if name not in profiles:
        new_route = create_marathon_route(name)
        profiles[name] = {
            "emeralds": 10, "streak": 1, "last_date": today_str,
            "task_num": 1, "helmet": "none", "unlocked_helmets": ["none"],
            "owned_vehicles": [], "upgraded_vehicles": [], "artifacts": [], "totems": 1, "luck_timer": 0,
            "strength_potions": 0,
            "strength_mob_task": None,
            "marathon_errors": 0, "marathon_error_details": [], "sound_enabled": True,
            "game_history": [], "boss_penalty_errors": 0, "helmet_protections": 0,
            "helmet_durability": {"none": 0},
            "marathon_route": new_route,
            "treasure_tasks": create_treasure_tasks(),
            "sage_task": create_sage_task(new_route),
            "sage_completed": False,
            "sage_artifact": None,
            "pet": "none",
            "pet_errors": 0,
            "pets_lost": 0,
            "marathon_elapsed_seconds": 0,
            "defeated_mob_worlds": [],
            "adaptive_tasks": {},
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
        if "owned_vehicles" not in p:
            p["owned_vehicles"] = list(p["upgraded_vehicles"])
        if "artifacts" not in p: p["artifacts"] = []
        if "totems" not in p: p["totems"] = 1
        if "luck_timer" not in p: p["luck_timer"] = 0
        had_permanent_strength = "strength_potion" in p.get("artifacts", [])
        if "strength_potions" not in p:
            p["strength_potions"] = 1 if had_permanent_strength else 0
        if had_permanent_strength:
            p["artifacts"].remove("strength_potion")
        if "strength_mob_task" not in p: p["strength_mob_task"] = None
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
        if "pet" not in p: p["pet"] = "none"
        if "pet_errors" not in p: p["pet_errors"] = 0
        if "pets_lost" not in p: p["pets_lost"] = 0
        if "marathon_elapsed_seconds" not in p: p["marathon_elapsed_seconds"] = 0
        if "defeated_mob_worlds" not in p: p["defeated_mob_worlds"] = []
        if "adaptive_tasks" not in p: p["adaptive_tasks"] = {}
        for helmet_id in p.get("unlocked_helmets", ["none"]):
            if helmet_id != "none" and helmet_id not in p["helmet_durability"]:
                p["helmet_durability"][helmet_id] = HELMETS.get(helmet_id, {}).get("max_durability", 0)
        equipped_helmet = p.get("helmet", "none")
        if equipped_helmet != "none" and p["helmet_durability"].get(equipped_helmet, 0) <= 0:
            p["helmet"] = "none"

    save_data(profiles)
    if remember_player:
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

def register_pet_error(profile):
    pet_id = profile.get("pet", "none")
    if pet_id == "none":
        return None
    errors = profile.get("pet_errors", 0) + 1
    if errors >= 2:
        profile["pet"] = "none"
        profile["pet_errors"] = 0
        profile["pets_lost"] = profile.get("pets_lost", 0) + 1
        return {"ran_away": True, "pet_name": PETS.get(pet_id, {}).get("name", "Питомец")}
    profile["pet_errors"] = errors
    return {"ran_away": False, "pet_name": PETS.get(pet_id, {}).get("name", "Питомец"), "errors": errors}

def make_math_task(ops_list, force_missing=False):
    """Generate a task for the currently selected player."""
    return generate_math_task(ops_list, player_name, force_missing=force_missing)


def make_task_for_step(profile, task_number):
    adaptive = profile.get("adaptive_tasks", {}) if profile else {}
    error_detail = adaptive.get(str(task_number), adaptive.get(task_number))
    if error_detail:
        question, answer, task_choices, _, expression = make_review_task(error_detail)
        return question, answer, task_choices, "adaptive", expression
    world_idx, _ = get_task_position(task_number)
    return make_math_task(get_route_world(profile, world_idx)["ops"])


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

def draw_pet_wolf(surf, cx, cy, anim_tick=0, small=False):
    scale = 0.7 if small else 1.0
    jump = int(abs(math.sin(anim_tick * 0.18)) * (5 if not small else 2))
    cy -= jump
    body_w, body_h = int(34 * scale), int(19 * scale)
    head_size = int(20 * scale)
    leg_w, leg_h = max(3, int(5 * scale)), max(5, int(10 * scale))
    fur = (155, 160, 165)
    light_fur = (205, 205, 200)
    pygame.draw.rect(surf, fur, (cx - body_w // 2, cy - body_h // 2, body_w, body_h))
    pygame.draw.rect(surf, light_fur, (cx + body_w // 2 - 4, cy - head_size // 2 - 5, head_size, head_size))
    pygame.draw.polygon(surf, fur, [
        (cx + body_w // 2 - 2, cy - head_size // 2 - 5),
        (cx + body_w // 2 + 3, cy - head_size // 2 - 13),
        (cx + body_w // 2 + 7, cy - head_size // 2 - 5),
    ])
    pygame.draw.rect(surf, (40, 40, 45), (cx + body_w // 2 + head_size - 7, cy - 4, 4, 4))
    pygame.draw.rect(surf, (65, 65, 70), (cx + body_w // 2 + 5, cy - 8, 3, 3))
    pygame.draw.rect(surf, (190, 40, 40), (cx + body_w // 2 - 3, cy + 3, head_size, 4))
    pygame.draw.rect(surf, fur, (cx - body_w // 2 + 4, cy + body_h // 2 - 1, leg_w, leg_h))
    pygame.draw.rect(surf, fur, (cx + body_w // 2 - 9, cy + body_h // 2 - 1, leg_w, leg_h))
    pygame.draw.line(surf, fur, (cx - body_w // 2, cy - 3), (cx - body_w // 2 - int(12 * scale), cy - int(13 * scale)), max(2, int(4 * scale)))

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

    elif item_type == "pet_wolf":
        draw_pet_wolf(surf, cx - 2, cy + 2, small=True)
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

def draw_pixel_cloud(surf, x, y, scale=1, color=(245, 250, 255)):
    """Draw a small blocky cloud used by animated world backgrounds."""
    blocks = (
        (0, 8, 58, 14),
        (12, 0, 22, 20),
        (32, 4, 18, 16),
    )
    for offset_x, offset_y, width, height in blocks:
        pygame.draw.rect(
            surf,
            color,
            (
                int(x + offset_x * scale),
                int(y + offset_y * scale),
                int(width * scale),
                int(height * scale),
            ),
        )


def draw_world_background(surf, world_idx, tick, ground_y):
    """Draw a lightweight animated background for the current biome."""
    world = WORLDS[world_idx]
    surf.fill(world["sky"])

    if world_idx == 0:
        pygame.draw.circle(surf, (255, 238, 120), (845, 125), 43)
        pygame.draw.polygon(
            surf,
            (105, 175, 105),
            [(0, ground_y), (0, 390), (150, 315), (300, 405), (455, 325), (620, ground_y)],
        )
        pygame.draw.polygon(
            surf,
            (80, 150, 85),
            [(430, ground_y), (610, 350), (735, 405), (875, 325), (1000, 395), (1000, ground_y)],
        )
        for cloud_index, (start_x, cloud_y, scale) in enumerate(
            ((40, 118, 1.0), (390, 165, 0.75), (720, 76, 0.9))
        ):
            speed = 0.28 + cloud_index * 0.04
            cloud_x = (start_x + tick * speed) % (WIDTH + 130) - 70
            draw_pixel_cloud(surf, cloud_x, cloud_y, scale)

    elif world_idx == 1:
        pygame.draw.circle(surf, (255, 235, 125), (820, 115), 52)
        pygame.draw.polygon(
            surf,
            (225, 185, 105),
            [(0, ground_y), (0, 410), (210, 350), (430, 420), (690, 345), (1000, 410), (1000, ground_y)],
        )
        pygame.draw.polygon(
            surf,
            (195, 145, 75),
            [(0, ground_y), (180, 430), (350, 455), (610, 395), (820, 450), (1000, 415), (1000, ground_y)],
        )
        for particle_index in range(13):
            sand_x = int((particle_index * 83 + tick * 1.1) % (WIDTH + 20) - 10)
            sand_y = 120 + (particle_index * 47) % 300
            sand_y += int(math.sin(tick * 0.04 + particle_index) * 8)
            pygame.draw.rect(surf, (190, 145, 80), (sand_x, sand_y, 3, 3))

    elif world_idx == 2:
        pygame.draw.circle(surf, (235, 245, 255), (835, 115), 38)
        pygame.draw.polygon(
            surf,
            (155, 195, 225),
            [(0, ground_y), (135, 270), (290, ground_y), (455, 235), (655, ground_y)],
        )
        pygame.draw.polygon(
            surf,
            (235, 245, 250),
            [(68, 385), (135, 270), (205, 375), (455, 235), (545, 350), (655, ground_y)],
        )
        pygame.draw.polygon(
            surf,
            (135, 180, 215),
            [(520, ground_y), (735, 320), (855, 410), (935, 295), (1000, 360), (1000, ground_y)],
        )
        for snow_index in range(18):
            wind = math.sin(tick * 0.03 + snow_index) * 18
            snow_x = int((snow_index * 61 + tick * 0.45 + wind) % WIDTH)
            snow_y = int((snow_index * 37 + tick * 0.8) % ground_y)
            snow_size = 2 + snow_index % 2
            pygame.draw.rect(surf, WHITE, (snow_x, snow_y, snow_size, snow_size))

    elif world_idx == 3:
        pygame.draw.circle(surf, (190, 45, 20), (820, 145), 58)
        pillars = (
            (35, 80, 210),
            (205, 110, 150),
            (690, 95, 230),
            (875, 75, 175),
        )
        for pillar_index, (pillar_x, pillar_width, pillar_height) in enumerate(pillars):
            pillar_color = (72 + pillar_index * 4, 18, 18)
            pygame.draw.rect(
                surf,
                pillar_color,
                (pillar_x, ground_y - pillar_height, pillar_width, pillar_height),
            )
            pygame.draw.rect(
                surf,
                (115, 28, 18),
                (pillar_x, ground_y - pillar_height, pillar_width, 8),
            )
        for ember_index in range(15):
            drift = int(math.sin(tick * 0.025 + ember_index) * 24)
            ember_x = (ember_index * 73 + drift) % WIDTH
            ember_y = ground_y - int((ember_index * 43 + tick * 0.9) % 390)
            ember_color = (255, 175, 35) if ember_index % 3 else (255, 75, 20)
            pygame.draw.rect(surf, ember_color, (ember_x, ember_y, 3, 5))

    else:
        pygame.draw.circle(surf, (120, 95, 155), (840, 120), 44)
        pygame.draw.circle(surf, world["sky"], (824, 105), 44)
        pygame.draw.polygon(
            surf,
            (38, 31, 55),
            [(0, ground_y), (0, 405), (165, 390), (235, 430), (370, 415), (445, ground_y)],
        )
        pygame.draw.polygon(
            surf,
            (45, 38, 65),
            [(585, ground_y), (650, 420), (805, 395), (895, 425), (1000, 390), (1000, ground_y)],
        )
        for mote_index in range(18):
            drift = math.sin(tick * 0.025 + mote_index) * 20
            mote_x = int((mote_index * 59 + drift) % WIDTH)
            mote_y = 85 + (mote_index * 41) % 350
            pulse = (tick // 12 + mote_index) % 3
            mote_color = ((155, 90, 220), (205, 145, 255), (105, 70, 175))[pulse]
            pygame.draw.rect(surf, mote_color, (mote_x, mote_y, 3, 3))

    pygame.draw.rect(
        surf,
        world["ground"],
        (0, ground_y, WIDTH, HEIGHT - ground_y),
    )
    pygame.draw.rect(surf, (40, 30, 20), (0, ground_y - 2, WIDTH, 3))

    for detail_index in range(22):
        detail_x = detail_index * 49 + (detail_index % 3) * 7
        if world_idx == 0:
            sway = int(math.sin(tick * 0.06 + detail_index) * 2)
            pygame.draw.line(
                surf,
                (55, 115, 40),
                (detail_x, ground_y + 20),
                (detail_x + sway, ground_y + 10),
                2,
            )
        elif world_idx == 1:
            detail_y = ground_y + 18 + detail_index % 3 * 8
            pygame.draw.rect(surf, (180, 130, 65), (detail_x, detail_y, 5, 2))
        elif world_idx == 2:
            detail_y = ground_y + 9 + detail_index % 4 * 7
            pygame.draw.rect(surf, (245, 250, 255), (detail_x, detail_y, 18, 3))
        elif world_idx == 3:
            crack_y = ground_y + 12 + detail_index % 4 * 8
            pygame.draw.line(
                surf,
                (235, 70, 15),
                (detail_x, crack_y),
                (detail_x + 12, crack_y + 4),
                2,
            )
        else:
            detail_y = ground_y + 10 + detail_index % 5 * 7
            pygame.draw.rect(surf, (95, 70, 125), (detail_x, detail_y, 4, 4))


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

def draw_librarian(surf, cx, cy, anim_tick=0):
    bob = int(math.sin(anim_tick * 0.08) * 2)
    cy += bob
    skin = (185, 135, 95)
    robe = (235, 225, 205)
    robe_shadow = (185, 170, 145)
    pygame.draw.rect(surf, robe, (cx - 19, cy - 2, 38, 44))
    pygame.draw.rect(surf, robe_shadow, (cx - 19, cy + 30, 38, 12))
    pygame.draw.rect(surf, skin, (cx - 18, cy - 34, 36, 34))
    pygame.draw.rect(surf, (170, 35, 35), (cx - 20, cy - 39, 40, 8))
    pygame.draw.rect(surf, (235, 225, 205), (cx - 13, cy - 45, 26, 7))
    pygame.draw.rect(surf, (65, 45, 30), (cx - 13, cy - 25, 26, 5))
    pygame.draw.rect(surf, (80, 180, 90), (cx - 11, cy - 23, 5, 4))
    pygame.draw.rect(surf, (80, 180, 90), (cx + 6, cy - 23, 5, 4))
    pygame.draw.rect(surf, skin, (cx - 5, cy - 19, 12, 14))
    pygame.draw.rect(surf, (110, 70, 45), (cx - 2, cy - 10, 10, 5))
    pygame.draw.rect(surf, skin, (cx - 27, cy + 7, 12, 25))
    pygame.draw.rect(surf, skin, (cx + 15, cy + 7, 12, 25))
    pygame.draw.rect(surf, (115, 70, 35), (cx - 22, cy + 18, 44, 19))
    pygame.draw.rect(surf, (235, 210, 115), (cx - 17, cy + 22, 34, 3))
    pygame.draw.line(surf, (70, 45, 25), (cx, cy + 19), (cx, cy + 36), 2)

def draw_ender_dragon_boss(surf, cx, cy, anim_tick=0, flash_red=False):
    wing_flap = int(math.sin(anim_tick * 0.22) * 24)
    d_col = (255, 150, 105) if flash_red else (185, 35, 35)
    wing_col = (255, 115, 70) if flash_red else (135, 25, 35)
    outline_col = (65, 10, 18)
    pygame.draw.polygon(surf, wing_col, [(cx - 20, cy), (cx - 110, cy - 45 + wing_flap), (cx - 40, cy + 25)])
    pygame.draw.polygon(surf, wing_col, [(cx + 20, cy), (cx + 110, cy - 45 + wing_flap), (cx + 40, cy + 25)])
    pygame.draw.line(surf, outline_col, (cx, cy), (cx - 110, cy - 45 + wing_flap), 4)
    pygame.draw.line(surf, outline_col, (cx, cy), (cx + 110, cy - 45 + wing_flap), 4)
    pygame.draw.rect(surf, d_col, (cx - 25, cy - 15, 50, 40), border_radius=4)
    pygame.draw.rect(surf, d_col, (cx - 8, cy + 25, 16, 35))
    pygame.draw.rect(surf, outline_col, (cx - 12, cy + 50, 24, 10))
    pygame.draw.rect(surf, d_col, (cx - 12, cy - 42, 24, 30))
    pygame.draw.rect(surf, d_col, (cx - 22, cy - 70, 44, 32))
    pygame.draw.rect(surf, outline_col, (cx - 16, cy - 50, 32, 12))
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
    if v_type == "foot":
        left_leg_x = sx - 9 + max(0, leg_swing)
        right_leg_x = sx + 1 + min(0, leg_swing)
        pygame.draw.rect(surf, (45, 55, 125), (left_leg_x, sy + 22, 8, 15))
        pygame.draw.rect(surf, (45, 55, 125), (right_leg_x, sy + 22, 8, 15))
        pygame.draw.rect(surf, (45, 40, 38), (left_leg_x - 1, sy + 35, 10, 5))
        pygame.draw.rect(surf, (45, 40, 38), (right_leg_x - 1, sy + 35, 10, 5))
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
TIMED_GAME_STATES = {"GAME", "MOB_BATTLE", "SAGE_CHALLENGE", "BOSS_BATTLE"}
base_y = 490
island_spacing = (WIDTH - 190) // (STEPS_PER_WORLD - 1)
platforms = [(95, base_y)] + [
    (95 + (i - 1) * island_spacing, base_y)
    for i in range(1, STEPS_PER_WORLD + 1)
]

def get_task_position(task_number):
    if task_number > TOTAL_QUESTS:
        return len(WORLDS) - 1, STEPS_PER_WORLD
    world_idx = max(0, (task_number - 1) // STEPS_PER_WORLD)
    step = ((task_number - 1) % STEPS_PER_WORLD) + 1
    return min(world_idx, len(WORLDS) - 1), step

last_player_name = get_last_player()
player_name = last_player_name if last_player_name in PLAYER_PROFILES else "Ксения"
preferred_player_name = last_player_name if last_player_name in PLAYER_PROFILES else None
login_show_all_players = preferred_player_name is None
player_data = get_player(
    player_name,
    apply_daily_bonus=False,
    remember_player=preferred_player_name is not None,
)
sound_enabled = player_data.get("sound_enabled", True)
game_state = "LOGIN"

task_num = player_data.get("task_num", 1) if player_data else 1
marathon_elapsed_seconds = float(player_data.get("marathon_elapsed_seconds", 0)) if player_data else 0.0
timer_save_accumulator = 0.0
combo_count = 0
current_world_idx, step_in_world = get_task_position(task_num)

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
question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
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
mob_strength_used = False

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
boss_speed_bonus = False
boss_previous_time = None

# Переменные библиотекаря
sage_question = ""
sage_answer = None
sage_choices = []
sage_msg = "Отгадай загадку с первой попытки!"
sage_finished = False
sage_won = False
sage_reward_name = ""
stats_page = 0
STATS_PER_PAGE = 6
history_page = 0
history_selected_index = None
HISTORY_PER_PAGE = 5
help_page = 0
mob_catalog_page = 0
exit_return_state = "LOGIN"

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

def format_duration(seconds):
    total_seconds = max(0, int(round(seconds or 0)))
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def persist_marathon_timer():
    if not player_name or not player_data:
        return
    elapsed = max(0, int(round(marathon_elapsed_seconds)))
    player_data["marathon_elapsed_seconds"] = elapsed
    all_data = load_data()
    if player_name.strip() in all_data:
        all_data[player_name.strip()]["marathon_elapsed_seconds"] = elapsed
        save_data(all_data)

def get_mob_max_hp():
    arts = player_data.get("artifacts", []) if player_data else []
    mob_id = get_route_world(player_data, current_world_idx).get("mob_id", "creeper")
    ability = MOB_ABILITIES.get(mob_id, {"base_hp": 3})
    base_hp = ability.get("base_hp", 3)
    if "sharp_sword" in arts:
        return max(1, base_hp - 1)
    return base_hp

def make_mob_battle_task(profile, world_idx):
    route_world = get_route_world(profile, world_idx)
    mob_id = route_world.get("mob_id", "creeper")
    ability = MOB_ABILITIES.get(mob_id, {})
    ops = list(route_world["ops"])
    if ability.get("kind") == "mixed":
        ops = ["+", "-"]
        if world_idx >= 2:
            ops.append("*")
        if world_idx >= 3:
            ops.append("/")
    return make_math_task(ops, force_missing=ability.get("kind") == "missing")

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
    global mob_battle_result_msg, mob_failed_reset, mob_strength_used

    game_state = "MOB_BATTLE"
    mob_max_hp = get_mob_max_hp()
    mob_hp = mob_max_hp
    mob_failed_reset = False
    mob_strength_used = player_data.get("strength_mob_task") == task_num
    if mob_strength_used:
        mob_max_hp = 1
        mob_hp = 1
    mob_battle_result_msg = "Реши пример, чтобы нанести удар!"
    mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_mob_battle_task(
        player_data, current_world_idx
    )

def start_boss_battle():
    global game_state, boss_streak, boss_max_hp
    global boss_msg, boss_won, boss_review_queue

    game_state = "BOSS_BATTLE"
    boss_max_hp = get_boss_max_hp()
    boss_streak = 0
    boss_won = False
    boss_review_queue = []
    seen_expressions = set()
    for error in player_data.get("marathon_error_details", []):
        error_key = (error.get("expr"), error.get("correct"))
        if error_key not in seen_expressions:
            seen_expressions.add(error_key)
            boss_review_queue.append(dict(error))
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
    global game_state, sage_question, sage_answer, sage_choices, sage_msg, sage_finished, sage_won, sage_reward_name
    game_state = "SAGE_CHALLENGE"
    sage_question, sage_answer, sage_choices = pick_logic_task(player_name)
    sage_msg = "На загадку даётся только одна попытка!"
    sage_finished = False
    sage_won = False
    sage_reward_name = ""

def reset_entire_marathon():
    global task_num, step_in_world, current_world_idx, hero_x, hero_y, target_x, target_y, is_moving
    global ten_errors, question_str, correct_ans, choices, current_op, clean_expr, game_state, message, message_color
    global player_data, marathon_elapsed_seconds, timer_save_accumulator

    task_num = 1
    current_world_idx, step_in_world = get_task_position(task_num)
    hero_x = float(platforms[step_in_world][0])
    hero_y = float(platforms[step_in_world][1] - 24)
    target_x, target_y = hero_x, hero_y
    is_moving = False
    ten_errors = []
    marathon_elapsed_seconds = 0.0
    timer_save_accumulator = 0.0

    all_data = load_data()
    if player_name.strip() in all_data:
        p = all_data[player_name.strip()]
        next_adaptive_tasks = create_adaptive_tasks(p)
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
        p["marathon_elapsed_seconds"] = 0
        p["defeated_mob_worlds"] = []
        p["adaptive_tasks"] = next_adaptive_tasks
        p["strength_mob_task"] = None
        save_data(all_data)
        player_data = p

    question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
    message = "Марафон начат сначала! Вперёд!"
    message_color = DARK_TEXT
    game_state = "GAME"

# Кнопки
btn_w, btn_h = 140, 54
start_btn_x = (WIDTH - (3 * btn_w + 40)) // 2
answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 235, btn_w, btn_h) for i in range(3)]
mob_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]
mob_strength_btn = pygame.Rect(WIDTH // 2 - 165, 500, 330, 42)
boss_answer_buttons = [pygame.Rect(start_btn_x + i * (btn_w + 20), 345, btn_w, btn_h) for i in range(3)]
sage_answer_buttons = [pygame.Rect(130 + i * 250, 370, 230, 58) for i in range(3)]
sage_continue_btn = pygame.Rect(WIDTH // 2 - 145, 470, 290, 48)

nav_workbench = pygame.Rect(480, 10, 100, 34)
nav_players = pygame.Rect(585, 10, 75, 34)
nav_sound = pygame.Rect(665, 10, 80, 34)
nav_reset_game = pygame.Rect(750, 10, 75, 34)
nav_fullscreen = pygame.Rect(830, 10, 80, 34)
nav_exit = pygame.Rect(915, 10, 70, 34)

confirm_reset_yes = pygame.Rect(WIDTH // 2 - 130, 310, 110, 42)
confirm_reset_no = pygame.Rect(WIDTH // 2 + 20, 310, 110, 42)
confirm_exit_yes = pygame.Rect(WIDTH // 2 - 130, 310, 110, 42)
confirm_exit_no = pygame.Rect(WIDTH // 2 + 20, 310, 110, 42)

player_play_buttons = {
    "Ксения": pygame.Rect(WIDTH // 2 - 105, 245, 150, 44),
    "Настя": pygame.Rect(WIDTH // 2 - 105, 330, 150, 44),
}
player_stats_buttons = {
    "Ксения": pygame.Rect(WIDTH // 2 + 55, 245, 150, 44),
    "Настя": pygame.Rect(WIDTH // 2 + 55, 330, 150, 44),
}
change_player_btn = pygame.Rect(WIDTH // 2 - 110, 390, 220, 42)
help_login_btn = pygame.Rect(WIDTH // 2 - 220, 465, 210, 46)
mob_catalog_btn = pygame.Rect(WIDTH // 2 + 10, 465, 210, 46)
exit_login_btn = pygame.Rect(WIDTH // 2 - 70, 518, 140, 34)
help_prev_btn = pygame.Rect(190, 515, 150, 42)
help_close_btn = pygame.Rect(WIDTH // 2 - 90, 515, 180, 42)
help_next_btn = pygame.Rect(660, 515, 150, 42)
catalog_prev_btn = pygame.Rect(190, 515, 150, 42)
catalog_close_btn = pygame.Rect(WIDTH // 2 - 90, 515, 180, 42)
catalog_next_btn = pygame.Rect(660, 515, 150, 42)

def get_login_profiles():
    if not login_show_all_players and preferred_player_name in PLAYER_PROFILES:
        return [preferred_player_name]
    return list(PLAYER_PROFILES)

def layout_login_profile_buttons(profile_names):
    row_positions = [285] if len(profile_names) == 1 else [245, 330]
    for profile_name, row_y in zip(profile_names, row_positions):
        player_play_buttons[profile_name].y = row_y
        player_stats_buttons[profile_name].y = row_y

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

tab_helmets_rect = pygame.Rect(120, 55, 145, 36)
tab_vehicles_rect = pygame.Rect(275, 55, 145, 36)
tab_artifacts_rect = pygame.Rect(430, 55, 145, 36)
tab_potions_rect = pygame.Rect(585, 55, 145, 36)
tab_pets_rect = pygame.Rect(740, 55, 145, 36)

# ==================== ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ ====================
async def main():
    global player_name, player_data, game_state, task_num, combo_count, current_world_idx, step_in_world
    global hero_x, hero_y, target_x, target_y, is_moving, move_progress, squash_val, anim_tick
    global sword_swing_timer, mob_flash_timer, ten_errors, question_str, correct_ans, choices, current_op, clean_expr
    global message, message_color, mob_hp, mob_max_hp, mob_task_str, mob_ans, mob_choices, mob_clean_expr, mob_op
    global mob_battle_result_msg, mob_failed_reset, mob_strength_used, boss_streak
    global boss_msg, boss_won, workbench_tab, stats_page, sound_enabled
    global history_page, history_selected_index
    global sage_msg, sage_finished, sage_won, sage_reward_name
    global marathon_elapsed_seconds, timer_save_accumulator, boss_speed_bonus, boss_previous_time
    global help_page, mob_catalog_page, exit_return_state
    global preferred_player_name, login_show_all_players

    running = True

    while running:
        anim_tick += 1
        mouse_pos = pygame.mouse.get_pos()
        login_profiles = get_login_profiles()
        if game_state == "LOGIN":
            layout_login_profile_buttons(login_profiles)

        if sword_swing_timer > 0: sword_swing_timer -= 1
        if mob_flash_timer > 0: mob_flash_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and hasattr(event, "pos"):
                mouse_pos = event.pos
                ensure_audio()

            if event.type == pygame.QUIT:
                persist_marathon_timer()
                running = False

            elif game_state == "LOGIN":
                selected_for_play = None
                selected_for_stats = None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not login_show_all_players and change_player_btn.collidepoint(mouse_pos):
                        login_show_all_players = True
                        continue
                    if exit_login_btn.collidepoint(mouse_pos):
                        exit_return_state = "LOGIN"
                        game_state = "CONFIRM_EXIT"
                        continue
                    if help_login_btn.collidepoint(mouse_pos):
                        help_page = 0
                        game_state = "HELP"
                        continue
                    if mob_catalog_btn.collidepoint(mouse_pos):
                        mob_catalog_page = 0
                        game_state = "MOB_CATALOG"
                        continue
                    for profile_name in login_profiles:
                        if player_play_buttons[profile_name].collidepoint(mouse_pos):
                            selected_for_play = profile_name
                        elif player_stats_buttons[profile_name].collidepoint(mouse_pos):
                            selected_for_stats = profile_name

                if selected_for_play:
                    player_name = selected_for_play
                    preferred_player_name = selected_for_play
                    login_show_all_players = False
                    request_browser_fullscreen()
                    player_data = get_player(player_name)
                    sound_enabled = player_data.get("sound_enabled", True)
                    marathon_elapsed_seconds = float(player_data.get("marathon_elapsed_seconds", 0))
                    timer_save_accumulator = 0.0
                    task_num = player_data.get("task_num", 1)
                    current_world_idx, step_in_world = get_task_position(task_num)
                    hero_x = float(platforms[step_in_world][0])
                    hero_y = float(platforms[step_in_world][1] - 24)
                    target_x, target_y = hero_x, hero_y
                    ten_errors = []
                    question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
                    game_state = "GAME"
                    if (
                        not player_data.get("sage_completed", False)
                        and player_data.get("sage_task") is not None
                        and task_num == player_data["sage_task"]
                    ):
                        start_sage_encounter()
                    elif (
                        step_in_world == get_route_world(player_data, current_world_idx).get("mob_step", 5)
                        and current_world_idx not in player_data.get("defeated_mob_worlds", [])
                    ):
                        start_mob_encounter()
                elif selected_for_stats:
                    player_name = selected_for_stats
                    preferred_player_name = selected_for_stats
                    player_data = get_player(player_name, apply_daily_bonus=False)
                    sound_enabled = player_data.get("sound_enabled", True)
                    marathon_elapsed_seconds = float(player_data.get("marathon_elapsed_seconds", 0))
                    timer_save_accumulator = 0.0
                    history_page = 0
                    history_selected_index = None
                    game_state = "HISTORY"

            elif game_state == "HELP":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if help_close_btn.collidepoint(mouse_pos):
                        game_state = "LOGIN"
                    elif help_page > 0 and help_prev_btn.collidepoint(mouse_pos):
                        help_page -= 1
                    elif help_page < len(HELP_PAGES) - 1 and help_next_btn.collidepoint(mouse_pos):
                        help_page += 1

            elif game_state == "MOB_CATALOG":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if catalog_close_btn.collidepoint(mouse_pos):
                        game_state = "LOGIN"
                    elif mob_catalog_page > 0 and catalog_prev_btn.collidepoint(mouse_pos):
                        mob_catalog_page -= 1
                    elif mob_catalog_page < len(MOB_POOLS) - 1 and catalog_next_btn.collidepoint(mouse_pos):
                        mob_catalog_page += 1

            elif game_state == "GAME":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if nav_fullscreen.collidepoint(mouse_pos):
                        request_browser_fullscreen()
                        continue
                    if nav_exit.collidepoint(mouse_pos):
                        persist_marathon_timer()
                        exit_return_state = "GAME"
                        game_state = "CONFIRM_EXIT"
                        continue
                    if nav_workbench.collidepoint(mouse_pos):
                        persist_marathon_timer()
                        game_state = "WORKBENCH"
                        continue
                    if nav_players.collidepoint(mouse_pos):
                        persist_marathon_timer()
                        login_show_all_players = True
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
                                    
                                    if is_treasure_task:
                                        message = f"СОКРОВИЩЕ НАЙДЕНО! (+{gain} изумр.)"
                                        message_color = MC_GOLD
                                    elif combo_count >= 5:
                                        message = f"СЕРИЯ x{combo_count} БЕЗ ОШИБОК! (+{gain} изумр.)"
                                        message_color = MC_GOLD
                                    else:
                                        message = f"Верно скрафчено! (+{gain} изумр.)"
                                        message_color = GREEN

                                    completed_task = task_num
                                    if completed_task % STEPS_PER_WORLD == 0:
                                        task_num += 1
                                        p["task_num"] = task_num
                                        save_data(all_data)
                                        player_data = p
                                        if completed_task == TOTAL_QUESTS:
                                            start_boss_battle()
                                        else:
                                            game_state = "REVIEW"
                                    else:
                                        task_num += 1
                                        step_in_world += 1
                                        target_x = platforms[step_in_world][0]
                                        target_y = platforms[step_in_world][1] - 24
                                        is_moving = True
                                        move_progress = 0.0
                                        p["task_num"] = task_num
                                        save_data(all_data)
                                        player_data = p
                                        question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)

                                else:
                                    wrong_val = choices[i]
                                    p["marathon_errors"] = p.get("marathon_errors", 0) + 1
                                    helmet_save = use_helmet_protection(p)
                                    if helmet_save:
                                        play_sound("hit")
                                    else:
                                        play_sound("wrong")
                                        p["boss_penalty_errors"] = p.get("boss_penalty_errors", 0) + 1
                                    pet_error = register_pet_error(p)
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
                                    if pet_error and pet_error["ran_away"]:
                                        message = f"{pet_error['pet_name']} убежал после второй ошибки!"
                                        message_color = RED
                                    spawn_dust(hero_x, hero_y, color=(80, 80, 80))

            elif game_state == "CONFIRM_RESET":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if confirm_reset_yes.collidepoint(mouse_pos):
                        reset_entire_marathon()
                    elif confirm_reset_no.collidepoint(mouse_pos):
                        game_state = "GAME"

            elif game_state == "CONFIRM_EXIT":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if confirm_exit_yes.collidepoint(mouse_pos):
                        persist_marathon_timer()
                        running = False
                    elif confirm_exit_no.collidepoint(mouse_pos):
                        game_state = exit_return_state

            elif game_state == "SAGE_CHALLENGE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if sage_finished:
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
                                    sage_finished = True
                                    sage_won = True
                                    sage_msg = f"Верно! Награда: {sage_reward_name}"
                                    play_sound("victory")
                                else:
                                    all_data = load_data()
                                    p = all_data[player_name.strip()]
                                    pet_error = register_pet_error(p)
                                    p["sage_completed"] = True
                                    p["sage_artifact"] = None
                                    save_data(all_data)
                                    player_data = p
                                    sage_finished = True
                                    sage_won = False
                                    sage_msg = "Библиотекарь уходит. В этом марафоне новой попытки не будет."
                                    if pet_error and pet_error["ran_away"]:
                                        sage_msg += f" {pet_error['pet_name']} тоже убежал!"
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
                                        history = p.setdefault("game_history", [])
                                        current_duration = max(1, int(round(marathon_elapsed_seconds)))
                                        previous_duration = history[-1].get("duration_seconds") if history else None
                                        boss_previous_time = previous_duration
                                        boss_speed_bonus = (
                                            isinstance(previous_duration, (int, float))
                                            and current_duration < int(previous_duration)
                                        )
                                        reward = 50 + (10 if boss_speed_bonus else 0)
                                        boss_msg = "ДРАКОН КРАЯ ПОВЕРЖЕН!"
                                        p["emeralds"] += reward
                                        p["marathon_elapsed_seconds"] = current_duration
                                        history.append({
                                            "completed_at": datetime.now().isoformat(timespec="minutes"),
                                            "errors": p.get("marathon_errors", 0),
                                            "boss_penalty_errors": p.get("boss_penalty_errors", 0),
                                            "helmet_protections": p.get("helmet_protections", 0),
                                            "error_details": [dict(item) for item in p.get("marathon_error_details", [])],
                                            "boss_hp": boss_max_hp,
                                            "grade": PLAYER_PROFILES.get(player_name, {}).get("grade"),
                                            "sage_artifact": p.get("sage_artifact"),
                                            "duration_seconds": current_duration,
                                            "previous_duration_seconds": previous_duration,
                                            "speed_bonus": boss_speed_bonus,
                                        })
                                        save_data(all_data)
                                        player_data = p
                                    else:
                                        play_sound("hit")
                                        boss_msg = f"Точный удар! Серия: {boss_streak} из {boss_max_hp}!"
                                        set_next_boss_task()
                                else:
                                    play_sound("wrong")
                                    pet_error = register_pet_error(p)
                                    save_data(all_data)
                                    player_data = p
                                    pet_suffix = f" {pet_error['pet_name']} убежал!" if pet_error and pet_error["ran_away"] else ""
                                    if p.get("totems", 0) > 0:
                                        p["totems"] -= 1
                                        save_data(all_data)
                                        player_data = p
                                        spawn_hit_sparks(280, 185, is_shield=True)
                                        boss_msg = f"Тотем спас от ошибки! Осталось тотемов: {p['totems']}.{pet_suffix}"
                                        set_next_boss_task()
                                    else:
                                        boss_streak = 0
                                        boss_msg = f"ОШИБКА (было {boss_ans})! Серия сброшена.{pet_suffix}"
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
                                _, step_in_world = get_task_position(task_num)
                                hero_x = float(platforms[step_in_world][0])
                                hero_y = float(platforms[step_in_world][1] - 24)
                                target_x, target_y = hero_x, hero_y
                                is_moving = False
                                all_data = load_data()
                                p = all_data[player_name.strip()]
                                p["task_num"] = task_num
                                p["strength_mob_task"] = None
                                save_data(all_data)
                                player_data = p
                                question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
                                message = "Моб победил! Уровень начат заново!"
                                message_color = RED
                                game_state = "GAME"
                            else:
                                all_data = load_data()
                                p = all_data[player_name.strip()]
                                p["emeralds"] += 5
                                p["strength_mob_task"] = None
                                defeated_worlds = p.setdefault("defeated_mob_worlds", [])
                                if current_world_idx not in defeated_worlds:
                                    defeated_worlds.append(current_world_idx)
                                save_data(all_data)
                                player_data = p
                                question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
                                message = "Моб повержен! Путь открыт!"
                                message_color = GREEN
                                game_state = "GAME"
                    else:
                        if mob_strength_btn.collidepoint(mouse_pos):
                            all_data = load_data()
                            p = all_data[player_name.strip()]
                            potion_count = p.get("strength_potions", 0)
                            if potion_count > 0 and mob_hp > 1 and not mob_strength_used:
                                p["strength_potions"] = potion_count - 1
                                p["strength_mob_task"] = task_num
                                mob_strength_used = True
                                mob_hp = 1
                                mob_max_hp = 1
                                mob_battle_result_msg = "Зелье выпито! У моба осталось 1 сердце."
                                play_sound("purchase")
                                save_data(all_data)
                                player_data = p
                            continue
                        for i, rect in enumerate(mob_answer_buttons):
                            if rect.collidepoint(mouse_pos):
                                all_data = load_data()
                                p = all_data[player_name.strip()]

                                if mob_choices[i] == mob_ans:
                                    play_sound("hit")
                                    pet_damage = 2 if p.get("pet", "none") != "none" else 1
                                    mob_hp = max(0, mob_hp - pet_damage)
                                    sword_swing_timer = 12
                                    mob_flash_timer = 10
                                    spawn_hit_sparks(720, 160)

                                    if mob_hp == 0:
                                        mob_battle_result_msg = (
                                            "ПОБЕДА! Волк помог: -2 жизни! (+5 изумрудов)"
                                            if pet_damage == 2 else
                                            "ПОБЕДА! Моб повержен! (+5 изумрудов!)"
                                        )
                                    else:
                                        mob_battle_result_msg = (
                                            f"Волк атаковал! -2 жизни. Осталось: {mob_hp}"
                                            if pet_damage == 2 else
                                            f"Точный удар! Осталось сердец: {mob_hp}"
                                        )
                                        mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_mob_battle_task(
                                            p, current_world_idx
                                        )
                                else:
                                    play_sound("wrong")
                                    pet_error = register_pet_error(p)
                                    save_data(all_data)
                                    player_data = p
                                    pet_suffix = f" {pet_error['pet_name']} убежал!" if pet_error and pet_error["ran_away"] else ""
                                    if p.get("totems", 0) > 0:
                                        p["totems"] -= 1
                                        save_data(all_data)
                                        player_data = p
                                        spawn_hit_sparks(280, 185, is_shield=True)
                                        mob_battle_result_msg = f"Тотем спас от сброса! Осталось: {p['totems']}.{pet_suffix}"
                                        mob_task_str, mob_ans, mob_choices, mob_op, mob_clean_expr = make_mob_battle_task(
                                            p, current_world_idx
                                        )
                                    else:
                                        mob_failed_reset = True
                                        mob_battle_result_msg = f"ОШИБКА! Правильно: {mob_ans}. Уровень сброшен!{pet_suffix}"
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
                            start_boss_battle()
                        else:
                            current_world_idx, step_in_world = get_task_position(task_num)
                            hero_x = float(platforms[step_in_world][0])
                            hero_y = float(platforms[step_in_world][1] - 24)
                            target_x, target_y = hero_x, hero_y
                            is_moving = False
                            question_str, correct_ans, choices, current_op, clean_expr = make_task_for_step(player_data, task_num)
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
                    elif tab_pets_rect.collidepoint(mouse_pos): workbench_tab = "PETS"

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
                                if v_code not in p.get("owned_vehicles", []) and p["emeralds"] >= w_info["v_cost"]:
                                    p["emeralds"] -= w_info["v_cost"]
                                    p.setdefault("owned_vehicles", []).append(v_code)
                                    play_sound("purchase")
                                    save_data(all_data)
                                elif v_code not in p["upgraded_vehicles"] and p["emeralds"] >= w_info["upg_cost"]:
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
                                elif pot_id == "strength_potion":
                                    if p.get("strength_potions", 0) < pot_info["max"] and p["emeralds"] >= pot_info["cost"]:
                                        p["emeralds"] -= pot_info["cost"]
                                        p["strength_potions"] = p.get("strength_potions", 0) + 1
                                        play_sound("purchase")
                                        save_data(all_data)
                                        player_data = p

                    elif workbench_tab == "PETS":
                        for idx, (pet_id, pet_info) in enumerate(PETS.items()):
                            _, _, b_pet = get_shop_row_rects(idx, len(PETS))
                            if b_pet.collidepoint(mouse_pos):
                                if p.get("pet", "none") == "none" and p["emeralds"] >= pet_info["cost"]:
                                    p["emeralds"] -= pet_info["cost"]
                                    p["pet"] = pet_id
                                    p["pet_errors"] = 0
                                    play_sound("purchase")
                                    save_data(all_data)
                                player_data = p

        if squash_val < 1.0:
            squash_val += 0.08
            if squash_val > 1.0: squash_val = 1.0

        cur_w = WORLDS[current_world_idx]
        cur_route = get_route_world(player_data, current_world_idx)
        cur_v_type = cur_w["vehicle_type"]
        has_vehicle = cur_v_type in player_data.get("owned_vehicles", []) if player_data else False
        is_upgraded = has_vehicle and cur_v_type in player_data.get("upgraded_vehicles", []) if player_data else False
        travel_type = cur_v_type if has_vehicle else "foot"

        if is_moving:
            move_speed = 0.13 if is_upgraded else 0.09 if has_vehicle else 0.055
            move_progress += move_speed
            if anim_tick % 3 == 0:
                spawn_dust(hero_x, hero_y + 20)

            if move_progress >= 1.0:
                move_progress = 1.0
                is_moving = False
                hero_x, hero_y = target_x, target_y
                squash_val = 0.75
                spawn_dust(hero_x, hero_y + 22)

                if (
                    not player_data.get("sage_completed", False)
                    and player_data.get("sage_task") == task_num
                ):
                    start_sage_encounter()
                elif (
                    step_in_world == cur_route.get("mob_step", 5)
                    and current_world_idx not in player_data.get("defeated_mob_worlds", [])
                ):
                    start_mob_encounter()
            else:
                prev_x = platforms[step_in_world - 1][0]
                hero_x = prev_x + (target_x - prev_x) * move_progress

                if travel_type in ["pig", "llama"]:
                    hero_y = (platforms[0][1] - 24) - 28 * abs(math.sin(move_progress * math.pi * 2))
                elif travel_type == "boat":
                    hero_y = (platforms[0][1] - 24)
                elif travel_type == "strider":
                    hero_y = (platforms[0][1] - 24) - 16 * abs(math.sin(move_progress * math.pi * 3))
                elif travel_type == "dragon":
                    hero_y = (platforms[0][1] - 24) - 75 * math.sin(move_progress * math.pi)
                else:
                    hero_y = (platforms[0][1] - 24) - 9 * abs(math.sin(move_progress * math.pi))

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
            card = pygame.Rect(WIDTH // 2 - 320, 55, 640, 500)
            pygame.draw.rect(screen, MC_GUI_BG, card)
            pygame.draw.rect(screen, MC_GUI_LIGHT, (card.left, card.top, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_DARK, (card.left, card.bottom - 3, card.width, 3))
            pygame.draw.rect(screen, MC_GUI_BLACK, card, 3)

            draw_emerald(screen, WIDTH // 2, 115, r=16)
            t1 = FONT_TITLE.render("Математика в Майнкрафте", True, DARK_TEXT)
            login_hint = "Продолжить игру" if len(login_profiles) == 1 else "Выбери игрока"
            t2 = FONT_MED.render(login_hint, True, (70, 80, 100))
            screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 145))
            screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 190))

            for profile_name in login_profiles:
                profile = PLAYER_PROFILES[profile_name]
                row_y = player_play_buttons[profile_name].centery
                profile_text = FONT_BIG.render(f"{profile_name} · {profile['grade']} класс", True, (35, 55, 95))
                screen.blit(profile_text, (card.x + 35, row_y - profile_text.get_height() // 2))
                draw_mc_button(
                    screen,
                    player_play_buttons[profile_name],
                    "Продолжить" if len(login_profiles) == 1 else "Играть",
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

            if len(login_profiles) == 1:
                draw_mc_button(
                    screen, change_player_btn, "Сменить игрока",
                    change_player_btn.collidepoint(mouse_pos),
                    font_pref=FONT_MED, custom_bg=(95, 100, 125)
                )

            draw_mc_button(
                screen, help_login_btn, "Как играть?",
                help_login_btn.collidepoint(mouse_pos),
                font_pref=FONT_BIG, custom_bg=(125, 85, 155)
            )
            draw_mc_button(
                screen, mob_catalog_btn, "Каталог мобов",
                mob_catalog_btn.collidepoint(mouse_pos),
                font_pref=FONT_BIG, custom_bg=(155, 85, 75)
            )
            draw_mc_button(
                screen, exit_login_btn, "Выход",
                exit_login_btn.collidepoint(mouse_pos),
                font_pref=FONT_SMALL, custom_bg=(155, 55, 55)
            )

        elif game_state == "HELP":
            screen.fill((45, 55, 75))
            help_card = pygame.Rect(100, 20, 800, 560)
            pygame.draw.rect(screen, (225, 225, 220), help_card)
            pygame.draw.rect(screen, (90, 65, 130), help_card, 4)

            page = HELP_PAGES[help_page]
            draw_emerald(screen, 155, 60, r=15)
            help_title = FONT_TITLE.render(page["title"], True, (75, 50, 115))
            screen.blit(help_title, (WIDTH // 2 - help_title.get_width() // 2, 43))
            page_label = FONT_SMALL.render(
                f"Страница {help_page + 1} из {len(HELP_PAGES)}",
                True, (90, 90, 100)
            )
            screen.blit(page_label, (WIDTH // 2 - page_label.get_width() // 2, 78))

            for line_idx, line in enumerate(page["lines"]):
                row = pygame.Rect(145, 108 + line_idx * 61, 710, 50)
                pygame.draw.rect(screen, (242, 242, 238) if line_idx % 2 == 0 else (232, 232, 228), row, border_radius=5)
                pygame.draw.rect(screen, (155, 145, 165), row, 1, border_radius=5)
                number_box = pygame.Rect(row.x + 8, row.y + 8, 34, 34)
                pygame.draw.rect(screen, (105, 80, 145), number_box, border_radius=5)
                number_text = FONT_MED.render(str(line_idx + 1), True, WHITE)
                screen.blit(number_text, (number_box.centerx - number_text.get_width() // 2, number_box.centery - number_text.get_height() // 2))
                line_font = FONT_MED if FONT_MED.size(line)[0] <= row.width - 60 else FONT_SMALL
                line_text = line_font.render(line, True, DARK_TEXT)
                screen.blit(line_text, (row.x + 52, row.centery - line_text.get_height() // 2))

            if help_page > 0:
                draw_mc_button(screen, help_prev_btn, "< Назад", help_prev_btn.collidepoint(mouse_pos), font_pref=FONT_MED)
            draw_mc_button(
                screen, help_close_btn, "К игрокам",
                help_close_btn.collidepoint(mouse_pos), font_pref=FONT_MED,
                custom_bg=(75, 115, 155)
            )
            if help_page < len(HELP_PAGES) - 1:
                draw_mc_button(screen, help_next_btn, "Дальше >", help_next_btn.collidepoint(mouse_pos), font_pref=FONT_MED)

        elif game_state == "MOB_CATALOG":
            screen.fill((38, 43, 52))
            catalog_card = pygame.Rect(45, 20, 910, 560)
            pygame.draw.rect(screen, (215, 215, 210), catalog_card)
            pygame.draw.rect(screen, (130, 55, 45), catalog_card, 4)

            catalog_world = WORLDS[mob_catalog_page]
            catalog_title = FONT_TITLE.render("КАТАЛОГ МОБОВ", True, (115, 45, 38))
            screen.blit(catalog_title, (WIDTH // 2 - catalog_title.get_width() // 2, 38))
            world_title = FONT_MED.render(catalog_world["name"], True, DARK_TEXT)
            screen.blit(world_title, (WIDTH // 2 - world_title.get_width() // 2, 78))

            for mob_index, (mob_id, mob_name) in enumerate(MOB_POOLS[mob_catalog_page]):
                ability = MOB_ABILITIES[mob_id]
                card_x = 75 + mob_index * 300
                mob_card = pygame.Rect(card_x, 118, 250, 340)
                pygame.draw.rect(screen, (238, 238, 232), mob_card, border_radius=8)
                pygame.draw.rect(screen, (105, 80, 70), mob_card, 2, border_radius=8)

                name_surface = FONT_BIG.render(mob_name, True, DARK_TEXT)
                screen.blit(name_surface, (mob_card.centerx - name_surface.get_width() // 2, 135))
                draw_mob(screen, mob_card.centerx, 235, mob_id, anim_tick=anim_tick)
                ability_surface = FONT_MED.render(ability["name"], True, (160, 55, 45))
                screen.blit(ability_surface, (mob_card.centerx - ability_surface.get_width() // 2, 300))
                draw_centered_wrapped_text(
                    screen, ability["desc"], FONT_SMALL, DARK_TEXT,
                    mob_card.centerx, 340, mob_card.width - 28, line_gap=5
                )

            page_surface = FONT_SMALL.render(
                f"Биом {mob_catalog_page + 1} из {len(MOB_POOLS)}",
                True, (90, 90, 95)
            )
            screen.blit(page_surface, (WIDTH // 2 - page_surface.get_width() // 2, 477))
            if mob_catalog_page > 0:
                draw_mc_button(screen, catalog_prev_btn, "< Назад", catalog_prev_btn.collidepoint(mouse_pos), font_pref=FONT_MED)
            draw_mc_button(
                screen, catalog_close_btn, "К игрокам",
                catalog_close_btn.collidepoint(mouse_pos), font_pref=FONT_MED,
                custom_bg=(75, 115, 155)
            )
            if mob_catalog_page < len(MOB_POOLS) - 1:
                draw_mc_button(screen, catalog_next_btn, "Дальше >", catalog_next_btn.collidepoint(mouse_pos), font_pref=FONT_MED)

        elif game_state == "GAME":
            draw_world_background(
                screen,
                current_world_idx,
                anim_tick,
                base_y + 15,
            )

            for i, (px, py) in enumerate(platforms):
                if i == 0:
                    continue
                b_rect = pygame.Rect(px - 26, py, 52, 28)
                pygame.draw.rect(screen, cur_w["plat"], b_rect)
                pygame.draw.rect(screen, cur_w["top_plat"], (b_rect.x, b_rect.y, b_rect.width, 7))
                pygame.draw.rect(screen, MC_GUI_BLACK, b_rect, 2)
                
                mob_step = cur_route.get("mob_step", 5)
                if i == mob_step and current_world_idx not in player_data.get("defeated_mob_worlds", []):
                    draw_mob(screen, px, py - 35, cur_route["mob_id"], anim_tick=anim_tick)
                sage_task = player_data.get("sage_task")
                sage_step = sage_task - current_world_idx * STEPS_PER_WORLD if sage_task is not None else -1
                if (
                    not player_data.get("sage_completed", False)
                    and i == sage_step
                    and step_in_world < sage_step
                ):
                    draw_librarian(screen, px, py - 42, anim_tick=anim_tick)
                if current_world_idx == 4 and i == 10 and task_num <= TOTAL_QUESTS:
                    pygame.draw.circle(screen, PURPLE, (px, py - 30), 12)
                    pygame.draw.circle(screen, WHITE, (px, py - 30), 4)

            for pt in particles:
                pygame.draw.rect(screen, pt[4], (int(pt[0]), int(pt[1]), pt[6], pt[6]))

            draw_steve_animated(screen, int(hero_x), int(hero_y), travel_type, is_upgraded,
                                helmet=player_data.get("helmet", "none"), 
                                anim_tick=anim_tick, is_moving=is_moving, squash=squash_val, sword_swing=sword_swing_timer)
            if player_data.get("pet", "none") == "wolf":
                pet_x = int(hero_x - 48 if not is_moving else hero_x - 58)
                draw_pet_wolf(screen, pet_x, int(hero_y + 23), anim_tick=anim_tick)

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
            pet_errors = player_data.get("pet_errors", 0)
            totem_info = f" | Т: {totems_cnt}" if totems_cnt > 0 else ""
            luck_info = f" | Уд: x2 ({luck_cnt})" if luck_cnt > 0 else ""
            errors_info = f" | О: {errors_cnt}" if errors_cnt > 0 else ""
            helmet_info = f" | Ш: {helmet_durability}" if equipped_helmet != "none" else ""
            pet_info = f" | Волк: {pet_errors}/2" if player_data.get("pet", "none") != "none" else ""
            time_info = f" | В: {format_duration(marathon_elapsed_seconds)}"

            bar_box = pygame.Rect(15, 10, 460, 34)
            pygame.draw.rect(screen, MC_GUI_BG, bar_box)
            pygame.draw.rect(screen, MC_GUI_LIGHT, (bar_box.left, bar_box.top, bar_box.width, 2))
            pygame.draw.rect(screen, MC_GUI_DARK, (bar_box.left, bar_box.bottom - 2, bar_box.width, 2))
            pygame.draw.rect(screen, MC_GUI_BLACK, bar_box, 2)

            draw_emerald(screen, 32, 27, r=8)
            info_label = f"{player_data['emeralds']}{totem_info}{luck_info}{helmet_info}{pet_info}{errors_info}{time_info} | {player_name}"
            info_font = FONT_MED if FONT_MED.size(info_label)[0] <= bar_box.width - 40 else FONT_SMALL
            info_txt = info_font.render(info_label, True, DARK_TEXT)
            screen.blit(info_txt, (46, 17))

            draw_mc_button(screen, nav_workbench, "Верстак", nav_workbench.collidepoint(mouse_pos), font_pref=FONT_SMALL)
            draw_mc_button(screen, nav_players, "Игроки", nav_players.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(95, 100, 125))
            sound_label = "Звук: да" if sound_enabled else "Звук: нет"
            draw_mc_button(screen, nav_sound, sound_label, nav_sound.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(70, 115, 155))
            draw_mc_button(screen, nav_reset_game, "Сброс", nav_reset_game.collidepoint(mouse_pos), font_pref=FONT_SMALL, custom_bg=(180, 60, 60))
            draw_mc_button(screen, nav_fullscreen, "Во весь", nav_fullscreen.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(90, 100, 120))
            draw_mc_button(screen, nav_exit, "Выход", nav_exit.collidepoint(mouse_pos), font_pref=FONT_TINY, custom_bg=(155, 55, 55))

            exp_w = 460
            exp_bg = pygame.Rect(WIDTH//2 - exp_w//2, 54, exp_w, 10)
            pygame.draw.rect(screen, (30, 30, 30), exp_bg)
            fill_w = int(min(task_num - 1, TOTAL_QUESTS) / TOTAL_QUESTS * exp_w)
            pygame.draw.rect(screen, (120, 255, 60), (exp_bg.x, exp_bg.y, fill_w, 10))
            pygame.draw.rect(screen, MC_GUI_BLACK, exp_bg, 2)

            v_title = cur_w["upg_name"] if is_upgraded else cur_w["v_name"] if has_vehicle else "Пешком"
            title_world = FONT_BIG.render(f"{cur_w['name']}  ({v_title})  [{min(task_num, 50)} / {TOTAL_QUESTS}]", True, DARK_TEXT if cur_w["dark_text"] else WHITE)
            screen.blit(title_world, (WIDTH//2 - title_world.get_width()//2, 72))

            is_treasure_task = task_num in player_data.get("treasure_tasks", [])
            if current_op == "adaptive" and task_num <= TOTAL_QUESTS:
                adaptive_label = "ПОВТОР ПРОШЛОЙ ОШИБКИ"
                if is_treasure_task:
                    adaptive_label += " · СОКРОВИЩЕ +2"
                draw_readable_badge(screen, WIDTH // 2, 118, adaptive_label, border_col=(115, 65, 155), text_col=(235, 205, 255), font=FONT_SMALL)
            elif is_treasure_task and task_num <= TOTAL_QUESTS:
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

        elif game_state == "CONFIRM_EXIT":
            screen.fill((40, 40, 45))
            exit_box = pygame.Rect(WIDTH // 2 - 240, 160, 480, 230)
            pygame.draw.rect(screen, MC_GUI_BG, exit_box)
            pygame.draw.rect(screen, MC_GUI_BLACK, exit_box, 3)

            exit_title = FONT_TITLE.render("Выйти из игры?", True, RED)
            exit_info = FONT_MED.render("Текущий прогресс будет сохранён.", True, DARK_TEXT)
            screen.blit(exit_title, (WIDTH // 2 - exit_title.get_width() // 2, 205))
            screen.blit(exit_info, (WIDTH // 2 - exit_info.get_width() // 2, 250))

            draw_mc_button(
                screen, confirm_exit_yes, "Да, выйти",
                confirm_exit_yes.collidepoint(mouse_pos), custom_bg=(190, 60, 60)
            )
            draw_mc_button(
                screen, confirm_exit_no, "Остаться",
                confirm_exit_no.collidepoint(mouse_pos), custom_bg=(70, 145, 80)
            )

        elif game_state == "CONFIRM_RESET":
            screen.fill((40, 40, 45))
            m_box = pygame.Rect(WIDTH // 2 - 240, 160, 480, 230)
            pygame.draw.rect(screen, MC_GUI_BG, m_box)
            pygame.draw.rect(screen, MC_GUI_BLACK, m_box, 3)

            t_r1 = FONT_TITLE.render("Сбросить марафон сначала?", True, RED)
            t_r2 = FONT_MED.render("Ты вернёшься на 1-й пример 1-го мира.", True, DARK_TEXT)
            t_r3 = FONT_SMALL.render("(Изумруды, экипировка, тотемы и питомец СОХРАНЯТСЯ)", True, (40, 140, 40))

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
            mob_ability = MOB_ABILITIES.get(cur_route["mob_id"], {})
            t_mob = FONT_TITLE.render(f"БИТВА СО СТРАЖЕМ: {mob_name.upper()}!", True, RED)
            screen.blit(t_mob, (WIDTH // 2 - t_mob.get_width() // 2, 38))

            pygame.draw.rect(screen, (100, 100, 105), (210, 205, 140, 20))
            pygame.draw.rect(screen, (60, 60, 65), (210, 205, 140, 20), 2)
            s_lbl = FONT_SMALL.render(player_name, True, DARK_TEXT)
            screen.blit(s_lbl, (280 - s_lbl.get_width() // 2, 95))
            draw_steve_animated(screen, 280, 175, travel_type, is_upgraded,
                                helmet=player_data.get("helmet", "none"),
                                anim_tick=anim_tick, sword_swing=sword_swing_timer)
            if player_data.get("pet", "none") == "wolf":
                draw_pet_wolf(screen, 220, 205, anim_tick=anim_tick)

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

            ability_label = f"{mob_ability.get('name', 'Без способности')}: {mob_ability.get('desc', '')}"
            ability_font = FONT_SMALL if FONT_SMALL.size(ability_label)[0] <= 700 else FONT_TINY
            ability_surface = ability_font.render(ability_label, True, (125, 45, 40))
            screen.blit(ability_surface, (WIDTH // 2 - ability_surface.get_width() // 2, 235))

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

                strength_count = player_data.get("strength_potions", 0)
                can_use_strength = strength_count > 0 and mob_hp > 1 and not mob_strength_used
                strength_label = (
                    f"Выпить Зелье Силы ({strength_count})"
                    if not mob_strength_used else
                    "Зелье Силы использовано"
                )
                draw_mc_button(
                    screen, mob_strength_btn, strength_label,
                    mob_strength_btn.collidepoint(mouse_pos) and can_use_strength,
                    can_use_strength, font_pref=FONT_SMALL,
                    custom_bg=(155, 55, 145) if can_use_strength else (100, 100, 105)
                )
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
            screen.fill((135, 195, 235))
            pygame.draw.rect(screen, (105, 150, 70), (0, 430, WIDTH, 170))
            for shelf_x in (75, 805):
                pygame.draw.rect(screen, (105, 65, 35), (shelf_x, 65, 120, 365))
                pygame.draw.rect(screen, (155, 105, 60), (shelf_x + 8, 75, 104, 345))
                for shelf_y in range(125, 421, 74):
                    pygame.draw.rect(screen, (80, 48, 25), (shelf_x + 5, shelf_y, 110, 8))
                    for book_idx, book_color in enumerate(((170, 45, 45), (45, 90, 155), (190, 150, 45), (65, 135, 70))):
                        book_x = shelf_x + 13 + book_idx * 24
                        pygame.draw.rect(screen, book_color, (book_x, shelf_y - 38, 17, 38))

            card = pygame.Rect(210, 25, 580, 535)
            pygame.draw.rect(screen, (198, 198, 198), card)
            pygame.draw.rect(screen, MC_GOLD, card, 4)
            title = FONT_TITLE.render("ЗАГАДКА БИБЛИОТЕКАРЯ", True, (75, 55, 100))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 48))
            draw_librarian(screen, WIDTH // 2, 155, anim_tick)

            if not sage_finished:
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
                box_color = (245, 235, 190) if sage_won else (235, 220, 220)
                border_color = MC_GOLD if sage_won else RED
                pygame.draw.rect(screen, box_color, reward_box, border_radius=8)
                pygame.draw.rect(screen, border_color, reward_box, 3, border_radius=8)
                result_title = "ЗАГАДКА РАЗГАДАНА!" if sage_won else "ОТВЕТ НЕВЕРНЫЙ"
                reward_title = FONT_TITLE.render(result_title, True, GREEN if sage_won else RED)
                screen.blit(reward_title, (WIDTH // 2 - reward_title.get_width() // 2, 270))
                result_text = (
                    f"Библиотекарь вручает тебе: {sage_reward_name}"
                    if sage_won else
                    sage_msg
                )
                draw_centered_wrapped_text(
                    screen, result_text, FONT_BIG,
                    (85, 60, 25), WIDTH // 2, 320, 450
                )
                draw_mc_button(
                    screen, sage_continue_btn,
                    "Забрать артефакт и продолжить" if sage_won else "Продолжить путь",
                    sage_continue_btn.collidepoint(mouse_pos), font_pref=FONT_MED,
                    custom_bg=(65, 145, 75) if sage_won else (105, 105, 120)
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
            draw_steve_animated(screen, 280, 185, travel_type, is_upgraded,
                                helmet=player_data.get("helmet", "none"),
                                anim_tick=anim_tick, sword_swing=sword_swing_timer)
            if player_data.get("pet", "none") == "wolf":
                draw_pet_wolf(screen, 220, 215, anim_tick=anim_tick)
            
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
                final_duration = player_data.get("marathon_elapsed_seconds", marathon_elapsed_seconds)
                if boss_previous_time is None:
                    speed_text = f"Время: {format_duration(final_duration)} · Это первый результат"
                elif boss_speed_bonus:
                    speed_text = (
                        f"НОВЫЙ РЕКОРД: {format_duration(final_duration)} "
                        f"(было {format_duration(boss_previous_time)}) · бонус +10!"
                    )
                else:
                    speed_text = (
                        f"Время: {format_duration(final_duration)} · "
                        f"прошлый результат: {format_duration(boss_previous_time)}"
                    )
                sub_reward = f"Награда за победу: +{60 if boss_speed_bonus else 50} ИЗУМРУДОВ!"
                screen.blit(FONT_MED.render(sub_info, True, WHITE), (WIDTH // 2 - FONT_MED.size(sub_info)[0] // 2, 325))
                screen.blit(FONT_SMALL.render(speed_text, True, MC_GOLD), (WIDTH // 2 - FONT_SMALL.size(speed_text)[0] // 2, 355))
                screen.blit(FONT_BIG.render(sub_reward, True, MC_EMERALD), (WIDTH // 2 - FONT_BIG.size(sub_reward)[0] // 2, 382))

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
            final_duration = player_data.get("marathon_elapsed_seconds", marathon_elapsed_seconds)
            summary = FONT_MED.render(
                f"Время: {format_duration(final_duration)} | Ошибок: {total_errors} | Шлем: {helmet_saves} | Босс: {boss_max_hp}",
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
                    record_duration = record.get("duration_seconds")
                    duration_label = format_duration(record_duration) if record_duration is not None else "—"
                    bonus_label = " · Рекорд +10" if record.get("speed_bonus") else ""
                    row_info = FONT_SMALL.render(
                        f"Время: {duration_label} · Ошибок: {record.get('errors', 0)} · Босс: {record.get('boss_hp', 5)}{bonus_label}",
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
            record_duration = record.get("duration_seconds")
            duration_label = format_duration(record_duration) if record_duration is not None else "—"
            bonus_label = " | Бонус скорости: +10" if record.get("speed_bonus") else ""
            detail_summary = FONT_SMALL.render(
                f"{completed_at} | Время: {duration_label} | Ошибок: {record.get('errors', 0)} | Босс: {record.get('boss_hp', 5)}{bonus_label}",
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
            draw_mc_button(screen, tab_pets_rect, "Питомцы", tab_pets_rect.collidepoint(mouse_pos),
                           custom_bg=(170, 170, 175) if workbench_tab == "PETS" else (90, 90, 95))

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

                    screen.blit(FONT_MED.render(f"{w_info['v_name']} -> {w_info['upg_name']}", True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 7))

                    is_owned = w_info["vehicle_type"] in player_data.get("owned_vehicles", [])
                    is_upg = w_info["vehicle_type"] in player_data.get("upgraded_vehicles", [])
                    if not is_owned:
                        transport_status = f"Купить: {w_info['v_cost']} · ускоряет движение"
                    elif not is_upg:
                        transport_status = f"Куплено · улучшить за {w_info['upg_cost']} (ещё быстрее)"
                    else:
                        transport_status = "Максимальная скорость"
                    screen.blit(FONT_SMALL.render(transport_status, True, (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 34))

                    if is_upg:
                        draw_mc_button(screen, b_upg, "Готово!", False, False, font_pref=FONT_SMALL)
                    elif not is_owned:
                        can_buy = player_data["emeralds"] >= w_info["v_cost"]
                        draw_mc_button(screen, b_upg, "Купить", b_upg.collidepoint(mouse_pos) and can_buy, can_buy, font_pref=FONT_SMALL)
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

                    if pot_id == "totem":
                        cnt = player_data.get("totems", 0)
                    elif pot_id == "luck":
                        cnt = 1 if player_data.get("luck_timer", 0) > 0 else 0
                    else:
                        cnt = player_data.get("strength_potions", 0)
                    screen.blit(FONT_BIG.render(f"{pot_info['name']} (В наличии: {cnt} из {pot_info['max']})", True, PURPLE), (slot_rect.right + 15, row_rect.y + 6))
                    screen.blit(FONT_SMALL.render(pot_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                    screen.blit(FONT_TINY.render(f"Цена: {pot_info['cost']} изумрудов", True, (0, 130, 40)), (slot_rect.right + 15, row_rect.y + 44))

                    is_full = cnt >= pot_info["max"]

                    if is_full:
                        draw_mc_button(screen, b_pot, "Максимум", False, False, font_pref=FONT_SMALL, custom_bg=(110, 110, 115))
                    else:
                        can_buy = player_data["emeralds"] >= pot_info["cost"]
                        draw_mc_button(screen, b_pot, "Купить", b_pot.collidepoint(mouse_pos) and can_buy, can_buy, font_pref=FONT_SMALL, custom_bg=(130, 60, 170))

            elif workbench_tab == "PETS":
                for idx, (pet_id, pet_info) in enumerate(PETS.items()):
                    row_rect, slot_rect, b_pet = get_shop_row_rects(idx, len(PETS))
                    pygame.draw.rect(screen, (232, 230, 220), row_rect)
                    pygame.draw.rect(screen, (125, 95, 70), row_rect, 2)

                    draw_mc_slot_frame(screen, slot_rect.x, slot_rect.y, 50)
                    draw_item_icon(screen, f"pet_{pet_id}", slot_rect.centerx, slot_rect.centery)

                    is_active = player_data.get("pet", "none") == pet_id
                    pet_errors = player_data.get("pet_errors", 0) if is_active else 0
                    screen.blit(FONT_BIG.render(pet_info["name"], True, (90, 65, 40)), (slot_rect.right + 15, row_rect.y + 6))
                    screen.blit(FONT_SMALL.render(pet_info["desc"], True, DARK_TEXT), (slot_rect.right + 15, row_rect.y + 28))
                    status_text = (
                        f"С вами · ошибок: {pet_errors} из 2"
                        if is_active else
                        f"Цена: {pet_info['cost']} изумрудов"
                    )
                    screen.blit(FONT_TINY.render(status_text, True, (0, 130, 40) if is_active else (80, 80, 80)), (slot_rect.right + 15, row_rect.y + 44))

                    if is_active:
                        draw_mc_button(screen, b_pet, "Рядом", False, False, font_pref=FONT_SMALL, custom_bg=(70, 140, 80))
                    else:
                        can_buy = player_data["emeralds"] >= pet_info["cost"]
                        draw_mc_button(screen, b_pet, "Купить", b_pet.collidepoint(mouse_pos) and can_buy, can_buy, font_pref=FONT_SMALL)

        pygame.display.flip()
        await asyncio.sleep(0)
        frame_seconds = min(clock.tick(60) / 1000.0, 0.25)
        timer_is_running = game_state in TIMED_GAME_STATES and not (game_state == "BOSS_BATTLE" and boss_won)
        if timer_is_running:
            marathon_elapsed_seconds += frame_seconds
            timer_save_accumulator += frame_seconds
            if timer_save_accumulator >= 10.0:
                persist_marathon_timer()
                timer_save_accumulator = 0.0

    pygame.quit()

# Запуск игры
asyncio.run(main())
