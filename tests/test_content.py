import unittest

from game_content import (
    ARTIFACTS,
    LOCATION_GROUPS,
    MOB_ABILITIES,
    MOB_POOLS,
    PLAYER_PROFILES,
    STEPS_PER_WORLD,
    TOTAL_QUESTS,
    WORLDS,
)


class ContentInvariantTests(unittest.TestCase):
    def test_marathon_has_five_worlds_with_ten_tasks(self):
        self.assertEqual(TOTAL_QUESTS, len(WORLDS) * STEPS_PER_WORLD)
        self.assertEqual(STEPS_PER_WORLD, 10)
        self.assertEqual(TOTAL_QUESTS, 50)

    def test_every_mob_has_an_ability(self):
        mob_ids = {mob_id for pool in MOB_POOLS for mob_id, _ in pool}
        self.assertEqual(mob_ids, set(MOB_ABILITIES))

    def test_artifact_charge_balance(self):
        for info in ARTIFACTS.values():
            self.assertGreater(info["max_charges"], 0)
            self.assertGreater(info["repair_cost"], 0)
            self.assertLess(info["repair_cost"], info["cost"])
        self.assertEqual(
            {item for item, info in ARTIFACTS.items() if info.get("librarian")},
            {"sharp_sword", "hint_book"},
        )
        self.assertEqual(ARTIFACTS["frog_wand"]["max_charges"], 2)
        self.assertNotIn("librarian", ARTIFACTS["frog_wand"])
        self.assertEqual(ARTIFACTS["heat_rune"]["max_charges"], 3)
        self.assertNotIn("librarian", ARTIFACTS["heat_rune"])

    def test_each_world_has_its_own_mob_pool(self):
        self.assertEqual(len(MOB_POOLS), len(WORLDS))
        self.assertTrue(all(len(pool) >= 3 for pool in MOB_POOLS))
        self.assertIn(("ice_golem", "Ледяной голем"), MOB_POOLS[2])

    def test_each_world_has_three_unique_locations(self):
        self.assertEqual(len(LOCATION_GROUPS), len(WORLDS))
        for locations in LOCATION_GROUPS:
            self.assertEqual(len(locations), 3)
            self.assertEqual(len({location["id"] for location in locations}), 3)
            self.assertTrue(all(location.get("theme") for location in locations))

    def test_player_profiles_keep_separate_difficulties(self):
        self.assertEqual(PLAYER_PROFILES["Ксения"]["difficulty"], "easy")
        self.assertEqual(PLAYER_PROFILES["Настя"]["difficulty"], "hard")


if __name__ == "__main__":
    unittest.main()
