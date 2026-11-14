import argparse
import json
import re
import sys
from pathlib import Path

import ollama

MODEL = "qwen3:4b"

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "schemas" / "examples" / "model_input.test_1.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "model_output.schema.json"

SYSTEM_PROMPT = (
    "You are a dialogue writer. You will receive a story and exactly two characters as JSON. "
    "Write a dialogue between those two characters that respects their personalities, "
    "their speech styles, the setting and the central conflict of the story. "
    "Respond ONLY with a single JSON object that follows the provided schema: "
    "no markdown, no code fences, no explanation. "
    "Use the characters' exact 'name' values in the 'speaker' field. Do not invent characters. "
    "Write the dialogue in the language given by 'output_language'. /no_think"
)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_user_prompt(data):
    story = data["story"]
    language = data.get("output_language", "es")

    lines = [
        "STORY",
        f"Title: {story['title']}",
        f"Premise: {story['premise']}",
        f"Setting: {story['setting']}",
        f"Central conflict: {story['central_conflict']}",
    ]
    if story.get("genre"):
        lines.append(f"Genre: {story['genre']}")
    if story.get("tone"):
        lines.append(f"Tone: {story['tone']}")

    for index, character in enumerate(data["characters"], start=1):
        personality = character["personality"]
        lines += [
            "",
            f"CHARACTER {index}",
            f"Name: {character['name']}",
            f"Age: {character['age']}",
            f"Role: {character['role']}",
            f"Appearance: {character['appearance']}",
            "Personality: " + " ".join(personality["traits"]),
        ]
        if personality.get("hidden_fear"):
            lines.append(f"Hidden fear / inner pressure: {personality['hidden_fear']}")
        if character.get("background"):
            lines.append(f"Background: {character['background']}")
        if character.get("speech_style"):
            lines.append(f"Speech style: {character['speech_style']}")

    lines += [
        "",
        "TASK",
        f"Write the dialogue in language '{language}'.",
    ]
    if data.get("max_turns"):
        lines.append(f"Use at most {data['max_turns']} dialogue turns.")
    if data.get("instruction"):
        lines.append(f"Additional direction: {data['instruction']}")

    lines += [
        "",
        "OUTPUT FORMAT",
        "A JSON object with this exact structure:",
        "{",
        '  "story_title": "<title of the story>",',
        f'  "language": "{language}",',
        '  "dialogue": [',
        '    {"speaker": "<exact character name>", "text": "<spoken words>", '
        '"stage_direction": "<optional action>"}',
        "  ]",
        "}",
        "Include at least 2 turns. Put gestures/actions in 'stage_direction', not in 'text'.",
    ]

    return "\n".join(lines)


def parse_response(content):
    """Parse the model reply, tolerating stray text around the JSON object."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("the model response contains no JSON object")
    return json.loads(match.group(0))


def validate_output(data, character_names, language):
    errors = []

    if not isinstance(data, dict):
        return ["response is not a JSON object"]

    for key in ("story_title", "language", "dialogue"):
        if key not in data:
            errors.append(f"missing required field '{key}'")

    if not isinstance(data.get("story_title"), str) or not data.get("story_title", "").strip():
        errors.append("'story_title' must be a non-empty string")

    if not isinstance(data.get("language"), str) or not re.fullmatch(
        r"[a-z]{2}(-[A-Z]{2})?", data.get("language", "")
    ):
        errors.append("'language' must be an ISO 639-1 code such as 'es'")
    elif data["language"] != language:
        errors.append(f"'language' is '{data['language']}' but '{language}' was requested")

    dialogue = data.get("dialogue")
    if not isinstance(dialogue, list):
        errors.append("'dialogue' must be an array")
        return errors

    if len(dialogue) < 2:
        errors.append("'dialogue' must contain at least 2 turns")

    for index, turn in enumerate(dialogue):
        where = f"dialogue[{index}]"
        if not isinstance(turn, dict):
            errors.append(f"{where} must be an object")
            continue
        speaker = turn.get("speaker")
        text = turn.get("text")
        if speaker not in character_names:
            errors.append(f"{where}.speaker '{speaker}' is not one of {sorted(character_names)}")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{where}.text must be a non-empty string")
        stage_direction = turn.get("stage_direction")
        if stage_direction is not None and not isinstance(stage_direction, str):
            errors.append(f"{where}.stage_direction must be a string when present")
        extra = set(turn) - {"speaker", "text", "stage_direction"}
        if extra:
            errors.append(f"{where} has unexpected fields: {sorted(extra)}")

    return errors


def print_dialogue(data):
    print(f"{data['story_title']}  [{data['language']}]")
    print()
    for turn in data["dialogue"]:
        direction = turn.get("stage_direction")
        prefix = f"({direction}) " if direction else ""
        print(f"{turn['speaker']}: {prefix}{turn['text']}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a dialogue from a structured story/characters JSON."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help=f"input JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument("--json", action="store_true", help="print the raw JSON response")
    parser.add_argument("--out", help="also save the raw JSON response to this path")
    args = parser.parse_args()

    input_path = Path(args.input)
    data = load_json(input_path)
    output_schema = load_json(OUTPUT_SCHEMA_PATH)

    character_names = {character["name"] for character in data["characters"]}
    language = data.get("output_language", "es")

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(data)},
        ],
        format=output_schema,
        stream=False,
        think=False,
    )

    content = response["message"]["content"]
    try:
        result = parse_response(content)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Could not parse JSON: {error}", file=sys.stderr)
        print("Raw response:", file=sys.stderr)
        print(content, file=sys.stderr)
        return 1

    errors = validate_output(result, character_names, language)
    if errors:
        print("Schema validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("Raw response:", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_dialogue(result)

    if args.out:
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nSaved JSON to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
