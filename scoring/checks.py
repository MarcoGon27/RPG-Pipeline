"""Objective rubric metrics (O1-O7). Pure functions: parsed artifacts in, numbers out.

Each `score_<stage>` returns a flat dict {score_name: value}. A metric that
cannot be computed (e.g. the O6 mean similarity of a single item) is left out
instead of being reported as 0. Embedding-based metrics (O6, O7) take an
`embed` callable: list[str] -> list[list[float]].
"""
import math
import re
from collections import Counter
from itertools import combinations

# O1 targets per "<stage>.<field>": (target_words, min_words, max_words).
# Inferred from the baseline artifacts (the prompts give no length guidance); tune freely.
# Per-item fields are keyed without their suffix: "world.rule" covers rule_0, rule_1, ...
# and "characters.personality" covers personality.<name>.
LENGTH_TARGETS: dict[str, tuple[int, int, int]] = {
    "world.narrative": (40, 25, 60),            # baseline: 38
    "world.rule": (10, 5, 18),                  # baseline: 7-10
    "characters.personality": (25, 15, 40),     # baseline: 22-24
    "conflict.conflict": (40, 25, 60),          # baseline: 40
    "dialog.dialogue": (150, 80, 250),          # baseline: 118; runs: 183-214
}


def words(text):
    return re.findall(r"\w+", text.lower())


# ---------- primitives ----------

def length_score(w, target):
    return max(0.0, 1 - abs(w - target) / target)


def repetition_3(text):
    """O5: share of repeated word 3-grams (None if the text has fewer than 3 words)."""
    toks = words(text)
    grams = [tuple(toks[i : i + 3]) for i in range(len(toks) - 2)]
    if not grams:
        return None
    return 1 - len(set(grams)) / len(grams)


def _cos(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def mean_sim(texts, embed):
    """Eq. (1): mean pairwise cosine similarity (None if fewer than 2 texts)."""
    if len(texts) < 2:
        return None
    vecs = embed(texts)
    sims = [_cos(a, b) for a, b in combinations(vecs, 2)]
    return sum(sims) / len(sims)


# ---------- per-metric helpers ----------

def o1(stage, fields):
    """fields: {field_name: text}. Emits length score and in-range flag per configured field."""
    out = {}
    for field, text in fields.items():
        key = re.sub(r"_\d+$", "", field.split(".")[0])
        cfg = LENGTH_TARGETS.get(f"{stage}.{key}")
        if cfg is None:
            continue
        target, lo, hi = cfg
        w = len(words(text))
        out[f"O1_length_score.{field}"] = length_score(w, target)
        out[f"O1_in_range.{field}"] = float(lo <= w <= hi)
    return out


def o5(texts):
    rep = repetition_3(" ".join(texts))
    return {} if rep is None else {"O5_repetition_3gram": rep}


def o6(label, texts, embed):
    sim = mean_sim(texts, embed)
    return {} if sim is None else {f"O6_internal_similarity.{label}": sim}


def o2(refs, names):
    return {"O2_referential_integrity": sum(r in names for r in refs) / len(refs)} if refs else {}


def _names(characters):
    return [c["name"] for c in characters["characters"]]


# ---------- per-stage scoring ----------

def score_world(world, embed=None):
    out = o1("world", {"narrative": world["narrative"], **{f"rule_{i}": r for i, r in enumerate(world["rules"])}})
    out.update(o5([world["narrative"], *world["rules"]]))
    if embed:
        out.update(o6("rules", world["rules"], embed))
    return out


def score_characters(characters, embed=None):
    chars = characters["characters"]
    names = _names(characters)
    texts = [f'{c["personality"]} {c["voice"]["tone"]}. {c["voice"]["speech_style"]}' for c in chars]
    fields = {}
    for c in chars:
        fields[f'personality.{c["name"]}'] = c["personality"]
    out = o1("characters", fields)
    out["O2_duplicate_names"] = float(len(names) - len(set(names)))
    out.update(o5(texts))
    if embed:
        out.update(o6("characters", texts, embed))
    return out


def score_conflict(conflict, characters, embed=None):
    names = set(_names(characters))
    rels = conflict["relationships"]
    refs = [n for r in rels for n in r["characters"]]
    in_conflict = set(refs) & names
    descs = [r["description"] for r in rels]
    out = o1("conflict", {"conflict": conflict["conflict"]})
    out.update(o2(refs, names))
    out["O2_self_pairs"] = float(sum(r["characters"][0] == r["characters"][1] for r in rels))
    out["O3_cast_coverage_conflict"] = len(in_conflict) / len(names)
    out.update(o5([conflict["conflict"], *descs]))
    if embed:
        out.update(o6("relationships", descs, embed))
    return out


def score_dialog(dialog, characters, conflict, embed=None):
    names = set(_names(characters))
    turns = dialog["dialogue"]
    speakers = {t["speaker"] for t in turns}
    in_conflict = {n for r in conflict["relationships"] for n in r["characters"]} & names
    wc = Counter()
    for t in turns:
        wc[t["speaker"]] += len(words(t["text"]))
    total = sum(wc.values())
    out = o1("dialog", {"dialogue": " ".join(t["text"] for t in turns)})
    out.update(o2([t["speaker"] for t in turns], names))
    if in_conflict:
        out["O3_cast_coverage_dialog"] = len(in_conflict & speakers) / len(in_conflict)
    out["O4_turns"] = float(len(turns))
    if total:
        out["O4_mean_words_per_turn"] = total / len(turns)
        out["O4_max_speaker_share"] = max(wc.values()) / total
    out.update(o5([t["text"] for t in turns]))
    return out


# ---------- O7 (across runs) ----------

def novelty(texts, embed):
    """O7: mean pairwise similarity of the same stage's output across k runs (lower = more novel)."""
    return mean_sim(texts, embed)
