from game.ai.controller import KeyboardAgentController
from game.ai.improvement import NoOpSelfImprovementPipeline
from game.engine.loop import SandboxGame
from game.systems.persistence import SaveLoadSystem
from game.ui.render import ConsoleRenderer
from game.world.generator import FlatWorldGenerator


def main() -> None:
    game = SandboxGame(
        world_generator=FlatWorldGenerator(),
        controller=KeyboardAgentController(),
        renderer=ConsoleRenderer(),
        persistence=SaveLoadSystem(),
        self_improvement=NoOpSelfImprovementPipeline(),
    )
    game.run()


if __name__ == "__main__":
    main()
