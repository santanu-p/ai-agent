from __future__ import annotations

from game.world.state_schema import WorldState
from game.world.storage import WorldStore, apply_operations


def rebuild_world(snapshot_id: str, store: WorldStore | None = None) -> WorldState:
    """Reconstruct deterministic world state from snapshot + contiguous diff chain."""
    store = store or WorldStore()
    state = store.load_snapshot(snapshot_id)

    for diff in store.diff_stream_from(state.world_version):
        if diff.base_world_version != state.world_version:
            break
        state = apply_operations(state, diff.operations)

    return state
