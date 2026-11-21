from pathlib import Path

from stages.stage import SCHEMAS_DIR, Stage


# TODO: fill in prompts and parameters
class World(Stage):
    name = "world"
    model = "qwen3:4b"
    system_prompt = ""
    user_prompt = ""
    output_path = Path("output/world.json")
    schema_path = SCHEMAS_DIR / "world.schema.json"
