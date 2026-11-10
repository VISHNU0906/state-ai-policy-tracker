"""Optional stage. Ask a language model to check each record the rules kept.

Off by default. It runs only when ANTHROPIC_API_KEY is set and the
`anthropic` package is installed; otherwise `refine` returns the records
unchanged and the dataset is exactly what the rules produced.

What it does per record: confirm or reject relevance against the written
definition, pick the category and sector from the fixed lists, and write a
one-sentence summary from the article text. Answers are constrained to a
JSON schema and cached on disk by record id, so a rerun costs nothing and
gives the same output.

What it does not do: find new records, change the state or the date, or see
anything except the headline and the article lead that the pipeline fetched.
"""
from __future__ import annotations

import json
import os

from . import config, taxonomy

MODEL = "claude-opus-5-5"
CACHE = config.RAW / "llm"

DEFINITION = """A record is relevant when a state government in India, or a body that answers to it
(departments, state police, state-run agencies and universities, district and city administrations)
or the state's High Court, takes a concrete step involving AI: a policy or draft, a new body or
institution, a signed agreement, a deployment in a public function, a budget commitment, a training
programme, or a rule. Not relevant: opinion, explainers, speeches with no concrete step, central
government actions, company news with no state body as a party, crime stories with no policy
response, and party politics."""

SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "category": {"type": "string", "enum": taxonomy.CATEGORIES},
        "sector": {"type": "string", "enum": taxonomy.SECTORS},
        "summary": {"type": "string"},
    },
    "required": ["relevant", "category", "sector", "summary"],
    "additionalProperties": False,
}


def _ask(client, rec: dict) -> dict:
    prompt = (
        f"{DEFINITION}\n\nState: {rec['state']}\nHeadline: {rec['title']}\n"
        f"Article lead: {rec.get('_body') or rec['summary']}\n\n"
        "Decide whether the record is relevant. Choose the single best category and sector. "
        "Write the summary as one plain sentence, at most 35 words, stating who did what. "
        "Use only facts present in the text above."
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=1024,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason != "end_turn":
        raise RuntimeError(f"unexpected stop_reason {resp.stop_reason}")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def refine(records: list[dict]) -> list[dict]:
    if os.environ.get("PIPELINE_OFFLINE") == "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        return records
    try:
        import anthropic
    except ImportError:
        print("llm: anthropic package not installed, skipping")
        return records

    client = anthropic.Anthropic()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    for rec in records:
        path = CACHE / f"{rec['record_id']}.json"
        try:
            if path.exists():
                ans = json.loads(path.read_text(encoding="utf-8"))
            else:
                ans = _ask(client, rec)
                path.write_text(json.dumps(ans, ensure_ascii=False), encoding="utf-8")
        except (anthropic.APIError, RuntimeError, ValueError, StopIteration) as exc:
            print(f"llm: {rec['record_id']} left as is ({type(exc).__name__})")
            out.append(rec)
            continue
        if rec["review_status"] == "reviewed":
            out.append(rec)            # a hand correction always wins over the model
            continue
        if not ans["relevant"]:
            rec["confidence"] = "low"  # flagged, not deleted: a person decides in overrides.csv
        rec.update(category=ans["category"], sector=ans["sector"], summary=ans["summary"],
                   summary_basis="llm_from_article_text", review_status="llm_checked")
        out.append(rec)
    return out
