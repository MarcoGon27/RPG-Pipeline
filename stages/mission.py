from stages.stage import SCHEMAS_DIR, Stage


SYSTEM_PROMPT = ""
USER_PROMPT = ""

# TODO: fill in prompts and parameters
class Mission(Stage):
    name = "mission"
    model = "qwen3:4b"
    system_prompt = SYSTEM_PROMPT 
    user_prompt = USER_PROMPT 
    filename = "mission.txt"
    schema_path = SCHEMAS_DIR / "conflict.schema.json"
