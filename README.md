# Story pipeline

A pipeline of LLM stages that generates a story artifact step by step. Each stage calls a local model (via Ollama), is forced to answer with a JSON schema, and feeds its output to the next stage.

```
idea ─▶ world ─▶ characters ─▶ conflict ─▶ dialog
```

## Setup

1. **Python dependencies** (Python 3.10+):
   ```bash
   pip install langfuse openai python-dotenv
   ```
2. **Ollama** running on `localhost:11434` with the model the stages use:
   ```bash
   ollama pull qwen3:4b
   curl http://localhost:11434/api/tags   # should return JSON
   ```
3. **Environment variables**: copy `.env.example` to `.env` and fill it in (Langfuse keys, and `USERNAME`, which is sent to Langfuse as the user id).

## Running

Run everything from the project root:

```bash
python pipeline.py "A heist in a floating city"   # every stage calls the LLM
python pipeline.py --live dialog                  # only dialog calls the LLM
python pipeline.py --live characters,conflict     # several live stages
python pipeline.py --live dialog --run-id my-test # name the run (default: a random UUID)
```

### Live vs baseline

Every stage runs in one of two modes:

- **Live**: the stage calls the LLM and generates its artifact. This is the stage you are testing.
- **Baseline**: the stage does **not** call the LLM. It loads a fixed, pre-written artifact from the `baseline/` folder instead, so the stages you are *not* testing give the same input every time. That makes your results comparable with everyone else's, and runs faster.

`--live` chooses which stages are live (`world`, `characters`, `conflict`, `dialog`, a comma-separated list, or `all`, the default). All the others use their baseline. For example, `--live dialog` loads the world, characters and conflict from `baseline/` and makes a single LLM call for the dialog.

The fixed artifacts are in [`baseline/`](baseline/), one file per stage: `world.txt`, `characters.txt`, `conflict.txt` and `dialog.txt`. They are JSON, matching the schemas in `schemas/`. They are shared by the whole group, so don't change them for a single experiment; agree on it first. To make a better baseline, copy a good file from `output/<run-id>/`.

The `idea` argument is only used by the `world` stage, so it has an effect only when `world` is live.

## Where things go

| Path | What it is |
|---|---|
| `pipeline.py` | Entry point: parses the CLI, runs the stages in order |
| `llm.py` | `run_llm(...)`: the single function that talks to the model (Ollama through the OpenAI client, traced by Langfuse) |
| `stages/` | One class per stage, on top of the `Stage` base class in `stages/stage.py` |
| `schemas/` | JSON schema for each stage's output; it constrains the model's answer |
| `baseline/` | Fixed artifacts used by the stages that aren't live (see above) |
| `output/<run-id>/` | Artifacts of each run, one folder per run (git-ignored). It has all four files: generated ones for live stages and copies of the baseline for the rest |

## Working on a stage

A stage is a class that sets a few attributes:

```python
class Dialog(Stage):
    name = "dialog-writer"
    model = "qwen3:4b"
    system_prompt = SYSTEM_PROMPT
    user_prompt = USER_PROMPT          # template filled with the stage's inputs
    filename = "dialog.txt"
    schema_path = SCHEMAS_DIR / "dialog.schema.json"
    params = {"reasoning_effort": "none", "temperature": 0.7}
```

- The user prompt is filled with `str.format`, so literal `{` and `}` must be written as `{{` and `}}`.
- Override `build_prompt(**inputs)` or `parse(output)` if a stage needs custom prompt building or validation.
- Inputs per stage: `world(idea)`, `characters(world)`, `conflict(world, characters)`, `dialog(world, characters, conflict)`.
- The `world`, `characters` and `conflict` prompts are still empty (`# TODO`), so they can't run live yet.

## Langfuse

Every call is traced. Traces carry the stage name, run id, live stages and the user id, and all stages of one run are grouped in a Langfuse session named after the run id (a UUID unless you pass `--run-id`).
