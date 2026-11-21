# Story pipeline

A pipeline of LLM stages that generates a story artifact step by step. Each stage calls a local model (via Ollama), is forced to answer with a JSON schema, and feeds its output to the next stage.

```
idea ─▶ world ─▶ characters ─▶ mission (conflict) ─▶ dialog
```

## Setup

1. **Python dependencies** (Python 3.10+):
   ```bash
   pip install langfuse openai python-dotenv
   ```
2. **Ollama** with the model the stages use (`qwen3:4b`). If you run it in Docker, the port must be published:
   ```bash
   docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama:latest
   docker exec ollama ollama pull qwen3:4b
   curl http://localhost:11434/api/tags   # should return JSON
   ```
3. **Environment variables**: copy `.env.example` to `.env` and fill it in (Langfuse keys, and `USERNAME`, which is sent to Langfuse as the user id).

## Running

Run everything from the project root:

```bash
python pipeline.py "A heist in a floating city"   # every stage calls the LLM
python pipeline.py --live dialog                  # only dialog calls the LLM
python pipeline.py --live characters,mission      # several live stages
python pipeline.py --live dialog --run-id my-test # name the run folder
```

- `--live` takes stage names (`world`, `characters`, `mission`, `dialog`) or `all` (default). Every stage that isn't live is loaded from `baseline/`, so you can test one stage without running the rest.
- The `idea` argument is only used by the `world` stage.

## Where things go

| Path | What it is |
|---|---|
| `pipeline.py` | Entry point: parses the CLI, runs the stages in order |
| `llm.py` | `run_llm(...)`: the single function that talks to the model (Ollama through the OpenAI client, traced by Langfuse) |
| `stages/` | One class per stage, on top of the `Stage` base class in `stages/stage.py` |
| `schemas/` | JSON schema for each stage's output; it constrains the model's answer |
| `baseline/` | Fixed artifacts (`world.txt`, `characters.txt`, `mission.txt`, `dialog.txt`) used by stages that aren't live. Changing them changes everyone's experiments, so agree on it first |
| `output/<run-id>/` | Artifacts of each run, one folder per run (git-ignored) |

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
- Inputs per stage: `world(idea)`, `characters(world)`, `mission(world, characters)`, `dialog(world, characters, conflict)`.
- The `world`, `characters` and `mission` prompts are still empty (`# TODO`), so they can't run live yet.

## Langfuse

Every call is traced. Traces carry the stage name, run id, live stages and the user id, and all stages of one run are grouped in a Langfuse session named after the run id.
