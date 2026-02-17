# game.world

This package defines deterministic world generation and runtime mutation for streamed chunks.

## Deterministic seed + patch history strategy

1. **Deterministic base generation**
   - `TerrainGenerator` derives chunk-local RNG seeds from `world_seed + chunk_x + chunk_y`.
   - Every client with the same world seed deterministically recreates the same base terrain and spawn layout.
2. **Persistent patch history**
   - `WorldStateStore` records append-only per-chunk patches to JSONL files.
   - Each patch ID is a content hash that includes chunk, parent patch ID, operation payload, and metadata.
   - The patch chain is validated on read to guarantee deterministic replay order.
3. **Reproduction rule**
   - Final chunk state is: `generated_chunk(world_seed, chunk_coord) + replay(patch_chain)`.
   - This supports cross-client consistency, save/load replay, and deterministic debugging.

## Chunk lifecycle hooks for AI systems

`ChunkStreamer` supports lifecycle hooks through the `ChunkLifecycleHook` protocol:

- `on_chunk_pre_load`: prepare spawn context, run risk checks.
- `on_chunk_loaded`: trigger spawn rules, quest injection, balancing and telemetry updates.
- `on_chunk_pre_unload`: flush pending AI decisions to patch ops.
- `on_chunk_unloaded`: release memory and close agent-local evaluators.

Typical hook responsibilities:

- **Spawn rules**: enrich deterministic spawn pools with live event modifiers.
- **Quest injection**: attach dynamic quest nodes to loaded NPC clusters.
- **Balancing adjustments**: apply AI-generated population/resource deltas and persist them as patch operations.
