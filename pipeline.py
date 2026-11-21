import sys

from stages.characters import Characters
from stages.dialog import Dialog
from stages.mission import Mission
from stages.world import World


def main():
    idea = sys.argv[1] if len(sys.argv) > 1 else "A short fantasy adventure"

    world = World().run(idea=idea)
    characters = Characters().run(idea=idea, world=world)
    mission = Mission().run(idea=idea, world=world, characters=characters)
    dialog = Dialog().run(story=mission, heroes=characters)

    print(dialog)


if __name__ == "__main__":
    main()
