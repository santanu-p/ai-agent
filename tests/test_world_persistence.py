import json
import tempfile
import unittest
from pathlib import Path

from game.world.persistence import WorldPersistenceManager
from game.world.rebuild import rebuild_world


class WorldPersistenceTests(unittest.TestCase):
    def test_snapshot_diff_and_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = WorldPersistenceManager(data_root=tmp, snapshot_interval_ticks=2, signing_key="k")

            state0 = {
                "world_id": "w1",
                "tick": 0,
                "entities": [{"entity_id": "e1", "kind": "npc", "attributes": {"hp": 10}, "version": 2}],
                "metadata": {"zone": "a"},
                "version": 2,
            }
            manager.persist_tick(state0)  # snapshot-0

            state1 = {
                "world_id": "w1",
                "tick": 1,
                "entities": [{"entity_id": "e1", "kind": "npc", "attributes": {"hp": 9}, "version": 2}],
                "metadata": {"zone": "a"},
                "version": 2,
            }
            manager.persist_tick(state1)  # diff-1

            state2 = {
                "world_id": "w1",
                "tick": 2,
                "entities": [
                    {"entity_id": "e1", "kind": "npc", "attributes": {"hp": 9}, "version": 2},
                    {"entity_id": "e2", "kind": "item", "attributes": {"qty": 1}, "version": 2},
                ],
                "metadata": {"zone": "b"},
                "version": 2,
            }
            manager.persist_tick(state2)  # snapshot-2

            rebuilt = rebuild_world(None, data_root=tmp, signing_key="k")
            self.assertEqual(rebuilt["tick"], 2)
            self.assertEqual(rebuilt["metadata"]["zone"], "b")
            self.assertEqual(len(rebuilt["entities"]), 2)

    def test_startup_recovery_skips_corrupt_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = WorldPersistenceManager(data_root=tmp, snapshot_interval_ticks=1, signing_key="k")
            state = {"world_id": "w", "tick": 1, "entities": [], "metadata": {}, "version": 2}
            snapshot_id = manager.write_snapshot(state)
            path = Path(tmp) / "snapshots" / f"{snapshot_id}.json"

            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["state"]["tick"] = 999
            path.write_text(json.dumps(raw), encoding="utf-8")

            recovered = manager.load_latest_valid_snapshot()
            self.assertEqual(recovered["tick"], 0)


if __name__ == "__main__":
    unittest.main()
