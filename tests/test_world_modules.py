from game.world.chunk_streamer import ChunkStreamer
from game.world.entity_registry import EntityRecord, EntityRegistry, EntityType
from game.world.terrain_generator import TerrainGenerator
from game.world.world_state_store import ChunkPatch, WorldStateStore


class _Hook:
    def __init__(self):
        self.calls = []

    def on_chunk_loaded(self, chunk):
        self.calls.append(("loaded", chunk.chunk_x, chunk.chunk_y))

    def apply_spawn_rules(self, chunk):
        self.calls.append(("spawn", chunk.chunk_x, chunk.chunk_y))

    def inject_quests(self, chunk):
        self.calls.append(("quest", chunk.chunk_x, chunk.chunk_y))

    def apply_balancing_adjustments(self, chunk):
        self.calls.append(("balance", chunk.chunk_x, chunk.chunk_y))

    def on_chunk_unloaded(self, coord):
        self.calls.append(("unloaded", coord[0], coord[1]))


def test_terrain_generation_is_deterministic():
    a = TerrainGenerator(world_seed="seed-1", generation_epoch=3).generate_chunk(2, 4)
    b = TerrainGenerator(world_seed="seed-1", generation_epoch=3).generate_chunk(2, 4)
    assert a.height_map == b.height_map
    assert a.biome_map == b.biome_map


def test_world_state_store_patch_replay(tmp_path):
    store = WorldStateStore(tmp_path)
    v1 = store.append_patch(0, 0, ChunkPatch(patch_id="p1", base_version=0, operations={"ore": 3}))
    assert v1 == 1
    v2 = store.append_patch(0, 0, ChunkPatch(patch_id="p2", base_version=1, operations={"ore": 5}))
    assert v2 == 2

    state = store.materialize_chunk_state(0, 0, base_state={"ore": 1})
    assert state["ore"] == 5
    assert store.verify_chunk_checksum(0, 0)


def test_entity_registry_tracks_types_and_chunks():
    registry = EntityRegistry()
    registry.upsert(EntityRecord("npc-1", EntityType.NPC, 0, 0))
    registry.upsert(EntityRecord("fauna-1", EntityType.FAUNA, 0, 0))
    registry.upsert(EntityRecord("res-1", EntityType.RESOURCE, 1, 0))

    assert len(registry.entities_in_chunk(0, 0)) == 2
    assert len(registry.list_by_type(EntityType.FAUNA)) == 1


def test_chunk_streamer_load_unload_and_hooks():
    hook = _Hook()
    streamer = ChunkStreamer(TerrainGenerator("seed"), view_distance_chunks=0, lifecycle_hooks=[hook])

    streamer.update_player_position(0, 0, chunk_size=16)
    assert (0, 0) in streamer.loaded_chunks

    streamer.update_player_position(32, 0, chunk_size=16)
    assert (2, 0) in streamer.loaded_chunks
    assert (0, 0) not in streamer.loaded_chunks

    event_types = [event[0] for event in hook.calls]
    assert "loaded" in event_types
    assert "spawn" in event_types
    assert "quest" in event_types
    assert "balance" in event_types
    assert "unloaded" in event_types
