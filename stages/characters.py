from pathlib import Path

from stages.stage import SCHEMAS_DIR, Stage


# TODO: fill in prompts and parameters
class Characters(Stage):
    name = "characters"
    model = "qwen3:4b"
    system_prompt = ""
    user_prompt = ""
    output_path = Path("output/characters.json")
    schema_path = SCHEMAS_DIR / "characters.schema.json"
