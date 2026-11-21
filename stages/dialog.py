from pathlib import Path

from stages.stage import SCHEMAS_DIR, Stage


class Dialog(Stage):
    name = "dialog-writer"
    model = "qwen3:4b"
    system_prompt = (
        "You are a dialog writer. You are going to receive two characters and a story. "
        "Your job is to generate a conversation between the two based on their personalities. /no_think"
    )
    user_prompt = "Story:\n{story}\n\nCharacters:\n{heroes}"
    output_path = Path("output/dialog.json")
    schema_path = SCHEMAS_DIR / "dialog.schema.json"
    params = {"reasoning_effort": "none", "temperature": 0.7}
