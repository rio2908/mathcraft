import unittest

from game_content import (
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

    def test_each_world_has_its_own_mob_pool(self):
        self.assertEqual(len(MOB_POOLS), len(WORLDS))
        self.assertTrue(all(len(pool) == 3 for pool in MOB_POOLS))

    def test_player_profiles_keep_separate_difficulties(self):
        self.assertEqual(PLAYER_PROFILES["Ксения"]["difficulty"], "easy")
        self.assertEqual(PLAYER_PROFILES["Настя"]["difficulty"], "hard")


if __name__ == "__main__":
    unittest.main()
