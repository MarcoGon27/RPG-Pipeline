import json
from pathlib import Path

from llm import run_llm

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class Stage:
    """Base class for a pipeline step: calls a model and saves its output as an artifact.

    Subclasses set the class attributes below and can override `build_prompt`
    or `parse` when they need custom behavior.
    """

    name: str
    model: str
    system_prompt: str
    user_prompt: str
    output_path: Path
    schema_path: Path  # JSON schema that constrains the model output
    params: dict = {}

    def build_prompt(self, **inputs):
        """Turn the inputs into the user prompt. Override for custom prompts."""
        return self.user_prompt.format(**inputs)

    def parse(self, output):
        """Post-process / validate the model output. Override for custom handling."""
        return output

    def run(self, **inputs):
        """Call the model, save the artifact to `output_path` and return it."""
        output = run_llm(
            name=self.name,
            model=self.model,
            system_prompt=self.system_prompt,
            user_prompt=self.build_prompt(**inputs),
            metadata={"stage": self.name},
            schema=json.loads(Path(self.schema_path).read_text(encoding="utf-8")),
            **self.params,
        )
        output = self.parse(output)

        path = Path(self.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        return output
