from stages.stage import SCHEMAS_DIR, Stage

SYSTEM_PROMPT = ""
USER_PROMPT = ""

# TODO: fill in prompts and parameters
class Characters(Stage):
    name = "characters"
    model = "qwen3:4b"
    system_prompt = SYSTEM_PROMPT 
    user_prompt = USER_PROMPT 
    filename = "characters.txt"
    schema_path = SCHEMAS_DIR / "characters.schema.json"
