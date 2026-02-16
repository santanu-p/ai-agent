# Local Sandbox Game Prototype

Minimal single-player sandbox scaffold with world generation, player movement/camera, and save/load flow.

## Project Structure

- `game/engine/` - main game loop orchestration
- `game/world/` - world models + generation interface/implementation
- `game/ai/` - agent and self-improvement interfaces + minimal implementations
- `game/systems/` - save/load systems
- `game/ui/` - camera rendering
- `server/` - optional local HTTP server scaffold
- `main.py` - sandbox entrypoint

## Setup

```bash
python3 --version
```

No external dependencies are required.

## Run

```bash
python3 main.py
```

Controls in-game:
- `w/a/s/d` move player
- `save` write `savegame.json`
- `load` read `savegame.json`
- `quit` exit loop

## Optional health server

```bash
python3 -m server.local_server
# then open http://127.0.0.1:8000/health
```

## Architecture Diagram

```text
+--------------------+
|      main.py       |
|  (entrypoint)      |
+---------+----------+
          |
          v
+--------------------+      +----------------------+
| game.engine.loop   +----->+ game.world.generator |
| run_game_loop()    |      | IWorldGenerator      |
+----+---------+-----+      +----------------------+
     |         |
     |         +------------> game.ai.controllers
     |                      (IAgentController,
     |                       ISelfImprovementPipeline)
     |
     +---------------------> game.ui.camera
     |
     +---------------------> game.systems.save_system

```
