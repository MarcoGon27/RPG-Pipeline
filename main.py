import sys

import ollama

MODEL = "qwen3:4b"

SYSTEM_PROMPT = (
    "You are a dialog writer. You are going to receive two characters and a story. "
    "Your job is to generate a conversation between the two based on their personalities."
)


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    history_file = sys.argv[1] if len(sys.argv) > 1 else "story.txt"
    hero_file = sys.argv[2] if len(sys.argv) > 2 else "hero.txt"

    story = read_file(history_file)
    heroes = read_file(hero_file)

    user_prompt = f"Story:\n{story}\n\nCharacters:\n{heroes}"

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        think=False,
    )

    for chunk in response:
        print(chunk["message"]["content"], end="", flush=True)
    print()


if __name__ == "__main__":
    main()
