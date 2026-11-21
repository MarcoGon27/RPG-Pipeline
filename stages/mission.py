from pathlib import Path

from stages.stage import SCHEMAS_DIR, Stage


# TODO: fill in prompts and parameters
class Mission(Stage):
    name = "mission"
    model = "qwen3:4b"
    system_prompt = ""
    user_prompt = ""
    output_path = Path("output/mission.json")
    schema_path = SCHEMAS_DIR / "conflict.schema.json"
