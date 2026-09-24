import random
import unittest

from game_content import (
    LOCATION_GROUPS,
    LOGIC_TASKS,
    MOB_POOLS,
    PLAYER_PROFILES,
    ROUTE_TEMPLATES,
    STEPS_PER_WORLD,
    TOTAL_QUESTS,
    WORLDS,
)
from game_tasks import (
    advance_heat_rune,
    advance_mob_regeneration,
    create_adaptive_tasks,
    create_marathon_route,
    create_sage_task,
    create_treasure_tasks,
    get_route_world,
    get_world_location,
    is_final_boss_position,
    make_math_task,
    make_review_task,
    pick_logic_task,
    pick_logic_task_with_history,
)


class MobRegenerationTests(unittest.TestCase):
    def test_heat_rune_pauses_then_resumes_existing_countdown(self):
        remaining, unprotected = advance_heat_rune(8.0, 3.0)
        self.assertEqual((remaining, unprotected), (5.0, 0.0))
        hp, elapsed, healed = advance_mob_regeneration(2, 3, 1.5, unprotected, 4.0)
        self.assertEqual((hp, elapsed, healed), (2, 1.5, 0))
        remaining, unprotected = advance_heat_rune(remaining, 6.0)
        self.assertEqual((remaining, unprotected), (0.0, 1.0))
        hp, elapsed, healed = advance_mob_regeneration(hp, 3, elapsed, unprotected, 4.0)
        self.assertEqual((hp, elapsed, healed), (2, 2.5, 0))
        hp, elapsed, healed = advance_mob_regeneration(hp, 3, elapsed, 1.5, 4.0)
        self.assertEqual((hp, elapsed, healed), (3, 0.0, 1))

    def test_three_quick_hits_defeat_golem(self):
        hp = 3
        elapsed = 0.0
        for delay in (0.0, 3.9, 3.9):
            hp, elapsed, healed = advance_mob_regeneration(hp, 3, elapsed, delay, 4.0)
            self.assertEqual(healed, 0)
            hp -= 1
            elapsed = 0.0  # Correct answer starts a fresh four-second window.
        self.assertEqual(hp, 0)

    def test_heals_on_four_second_boundary_and_repeats_until_full(self):
        hp, elapsed, healed = advance_mob_regeneration(1, 3, 0.0, 3.99, 4.0)
        self.assertEqual((hp, healed), (1, 0))
        hp, elapsed, healed = advance_mob_regeneration(hp, 3, elapsed, 0.01, 4.0)
        self.assertEqual((hp, healed), (2, 1))
        hp, elapsed, healed = advance_mob_regeneration(hp, 3, elapsed, 4.0, 4.0)
        self.assertEqual((hp, elapsed, healed), (3, 0.0, 1))

    def test_never_revives_defeated_mob_or_exceeds_maximum(self):
        self.assertEqual(advance_mob_regeneration(0, 3, 0.0, 10.0, 4.0), (0, 0.0, 0))
        self.assertEqual(advance_mob_regeneration(2, 2, 0.0, 10.0, 4.0), (2, 0.0, 0))
        self.assertEqual(advance_mob_regeneration(1, 3, 0.0, 20.0, 4.0), (3, 0.0, 2))


def calculate(expression):
    parts = expression.strip().split()
    if len(parts) == 1:
        return int(parts[0])
    left, operation, right = parts
    left = int(left)
    right = int(right)
    if operation == "+":
        return left + right
    if operation == "-":
        return left - right
    if operation == "x":
        return left * right
    if operation == ":":
        return left // right
    raise AssertionError(f"Unknown operation: {operation}")


class RouteGenerationTests(unittest.TestCase):
    def setUp(self):
        random.seed(20260921)

    def test_route_matches_profile_and_world_rules(self):
        for profile_name, profile in PLAYER_PROFILES.items():
            with self.subTest(profile=profile_name):
                route = create_marathon_route(profile_name)
                templates = ROUTE_TEMPLATES[profile["difficulty"]]
                self.assertEqual(len(route), len(WORLDS))
                for world_index, world_route in enumerate(route):
                    self.assertIn(
                        (world_route["mob_id"], world_route["mob_name"]),
                        MOB_POOLS[world_index],
                    )
                    self.assertIn(world_route["ops"], templates[world_index])
                    self.assertIn(
                        world_route["location_id"],
                        {location["id"] for location in LOCATION_GROUPS[world_index]},
                    )
                    self.assertGreaterEqual(world_route["mob_step"], 3)
                    self.assertLessEqual(world_route["mob_step"], 8)

    def test_custom_profile_uses_saved_difficulty(self):
        route = create_marathon_route("Alex", difficulty="hard")
        for world_index, world_route in enumerate(route):
            self.assertIn(world_route["ops"], ROUTE_TEMPLATES["hard"][world_index])

    def test_treasure_has_one_task_in_each_world(self):
        treasure_tasks = create_treasure_tasks()
        self.assertEqual(len(treasure_tasks), len(WORLDS))
        for world_index, task_number in enumerate(treasure_tasks):
            self.assertGreaterEqual(
                task_number,
                world_index * STEPS_PER_WORLD + 1,
            )
            self.assertLessEqual(
                task_number,
                (world_index + 1) * STEPS_PER_WORLD,
            )

    def test_librarian_avoids_mobs_and_world_boundaries(self):
        route = create_marathon_route("Ксения")
        occupied = {
            world_index * STEPS_PER_WORLD + world["mob_step"]
            for world_index, world in enumerate(route)
        }
        task_number = create_sage_task(route, start_at=17)
        self.assertGreaterEqual(task_number, 17)
        self.assertLess(task_number, TOTAL_QUESTS)
        self.assertNotEqual(task_number % STEPS_PER_WORLD, 0)
        self.assertNotIn(task_number, occupied)

    def test_saved_route_is_used_and_missing_route_has_fallback(self):
        route = create_marathon_route("Настя")
        self.assertIs(get_route_world({"marathon_route": route}, 2), route[2])
        fallback = get_route_world({}, 2)
        self.assertEqual(fallback["ops"], WORLDS[2]["ops"])
        self.assertEqual(fallback["mob_id"], WORLDS[2]["mob_id"])

    def test_saved_location_is_restored_and_old_save_uses_base_location(self):
        profile = {
            "marathon_route": [
                {"location_id": locations[-1]["id"]}
                for locations in LOCATION_GROUPS
            ]
        }
        for world_index, locations in enumerate(LOCATION_GROUPS):
            selected = get_world_location(profile, world_index)
            self.assertEqual(selected["id"], locations[-1]["id"])
            self.assertEqual(selected["name"], locations[-1]["name"])
            self.assertIn("vehicle_type", selected)

            fallback = get_world_location({}, world_index)
            self.assertEqual(fallback["id"], locations[0]["id"])

    def test_only_the_last_island_starts_the_final_boss(self):
        self.assertTrue(is_final_boss_position(TOTAL_QUESTS, len(WORLDS) - 1, STEPS_PER_WORLD))
        self.assertFalse(is_final_boss_position(TOTAL_QUESTS - 1, len(WORLDS) - 1, STEPS_PER_WORLD - 1))
        self.assertFalse(is_final_boss_position(TOTAL_QUESTS, len(WORLDS) - 2, STEPS_PER_WORLD))


class MathTaskTests(unittest.TestCase):
    def setUp(self):
        random.seed(20260921)

    def assert_valid_task(self, task):
        question, answer, choices, _, expression = task
        self.assertEqual(len(choices), 3)
        self.assertEqual(len(set(choices)), 3)
        self.assertIn(answer, choices)
        self.assertIn("?", question)

        if "?" in expression:
            left, right = expression.split("=")
            self.assertEqual(
                calculate(left.replace("?", str(answer))),
                calculate(right.replace("?", str(answer))),
            )
        else:
            self.assertEqual(calculate(expression), answer)

    def test_all_operations_generate_valid_choices_and_answers(self):
        for profile_name in PLAYER_PROFILES:
            for operation in ("+", "-", "*", "/"):
                for force_missing in (False, True):
                    for _ in range(100):
                        with self.subTest(
                            profile=profile_name,
                            operation=operation,
                            force_missing=force_missing,
                        ):
                            task = make_math_task(
                                [operation],
                                profile_name,
                                force_missing=force_missing,
                            )
                            self.assertEqual(task[3], operation)
                            self.assert_valid_task(task)

    def test_easy_and_hard_addition_use_different_ranges(self):
        easy_answers = [
            make_math_task(["+"], "Ксения")[1]
            for _ in range(100)
        ]
        hard_answers = [
            make_math_task(["+"], "Настя")[1]
            for _ in range(100)
        ]
        self.assertLessEqual(max(easy_answers), 20)
        self.assertGreater(max(hard_answers), 20)

    def test_custom_profile_math_uses_saved_difficulty(self):
        answers = [
            make_math_task(["+"], "Alex", difficulty="hard")[1]
            for _ in range(100)
        ]
        self.assertGreater(max(answers), 20)

    def test_review_task_keeps_correct_and_wrong_answers(self):
        task = make_review_task({
            "expr": "7 + ? = 15",
            "correct": 8,
            "wrong": 7,
        })
        self.assertEqual(task[0], "7 + ? = 15")
        self.assertEqual(task[1], 8)
        self.assertIn(8, task[2])
        self.assertIn(7, task[2])
        self.assertEqual(len(set(task[2])), 3)

    def test_logic_task_does_not_repeat_previous_question(self):
        previous = LOGIC_TASKS["easy"][0]["question"]
        question, answer, choices = pick_logic_task("Ксения", previous)
        self.assertNotEqual(question, previous)
        self.assertIn(answer, choices)
        self.assertEqual(len(choices), 3)

    def test_logic_pools_are_large_and_have_valid_unique_answers(self):
        for difficulty in ("easy", "hard"):
            tasks = LOGIC_TASKS[difficulty]
            self.assertGreaterEqual(len(tasks), 24)
            self.assertEqual(len({task["question"] for task in tasks}), len(tasks))
            for task in tasks:
                self.assertEqual(len(task["choices"]), 3)
                self.assertEqual(len(set(task["choices"])), 3)
                self.assertIn(task["answer"], task["choices"])

    def test_librarian_questions_do_not_repeat_until_pool_is_exhausted(self):
        for difficulty in ("easy", "hard"):
            history = []
            for _ in LOGIC_TASKS[difficulty]:
                question, answer, choices, history = pick_logic_task_with_history(
                    "Игрок", history, difficulty
                )
                self.assertEqual(len(history), len(set(history)))
                self.assertIn(answer, choices)
            self.assertEqual(len(history), len(LOGIC_TASKS[difficulty]))
            last_question = history[-1]
            question, _, _, history = pick_logic_task_with_history(
                "Игрок", history, difficulty
            )
            self.assertNotEqual(question, last_question)
            self.assertEqual(history, [question])

    def test_librarian_histories_are_independent(self):
        first, _, _, first_history = pick_logic_task_with_history("Настя", [], "hard")
        second, _, _, second_history = pick_logic_task_with_history("Ксения", [], "easy")
        self.assertEqual(first_history, [first])
        self.assertEqual(second_history, [second])


class AdaptiveTaskTests(unittest.TestCase):
    def setUp(self):
        random.seed(20260921)

    def test_repeated_error_is_prioritized_and_worlds_are_distinct(self):
        repeated = {"expr": "7 + ? = 15", "correct": 8, "wrong": 7}
        profile = {
            "game_history": [{
                "error_details": [
                    repeated,
                    repeated,
                    {"expr": "6 x 7", "correct": 42, "wrong": 36},
                    {"expr": "18 : 3", "correct": 6, "wrong": 9},
                    {"expr": "50 - 17", "correct": 33, "wrong": 23},
                ],
            }],
            "marathon_error_details": [],
        }

        adaptive = create_adaptive_tasks(profile)

        self.assertEqual(len(adaptive), 3)
        self.assertIn("7 + ? = 15", {
            detail["expr"] for detail in adaptive.values()
        })
        worlds = {
            (int(task_number) - 1) // STEPS_PER_WORLD
            for task_number in adaptive
        }
        self.assertEqual(len(worlds), 3)

    def test_no_errors_produces_no_adaptive_tasks(self):
        self.assertEqual(create_adaptive_tasks({}), {})


if __name__ == "__main__":
    unittest.main()
