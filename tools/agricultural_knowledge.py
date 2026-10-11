"""
Agricultural Knowledge Tool
Searches the local curated knowledge base for relevant entries.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from models.schemas import KnowledgeEntry, ResearchResult

_KB_PATH = Path(__file__).parent.parent / "data" / "agricultural_knowledge.json"
_knowledge_base: Optional[list[dict]] = None


def _load_kb() -> list[dict]:
    global _knowledge_base
    if _knowledge_base is None:
        with _KB_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _knowledge_base = data.get("entries", [])
    return _knowledge_base


def _score_entry(entry: dict, crop: str, symptoms_text: str) -> float:
    """
    Simple keyword-based relevance scoring.
    Returns a float 0..1 (higher = more relevant).
    """
    score = 0.0
    crop_lower = crop.lower().strip()
    text_lower = symptoms_text.lower()

    entry_crop = entry.get("crop", "").lower()
    # Exact crop match
    if entry_crop == crop_lower:
        score += 0.5
    elif entry_crop == "general":
        score += 0.1
    # Partial crop match
    elif crop_lower in entry_crop or entry_crop in crop_lower:
        score += 0.3

    keywords: list[str] = entry.get("keywords", [])
    matched_kw = sum(1 for kw in keywords if re.search(re.escape(kw), text_lower))
    if keywords:
        score += 0.5 * (matched_kw / len(keywords))

    return round(min(score, 1.0), 4)


def search_knowledge_base(
    crop_name: str,
    symptoms: str,
    top_k: int = 3,
) -> ResearchResult:
    """
    Search the local agricultural knowledge base.

    Args:
        crop_name:  Name of the crop reported by the farmer.
        symptoms:   Description of observed symptoms.
        top_k:      Maximum number of results to return.

    Returns:
        ResearchResult with matching KnowledgeEntry objects.
    """
    entries = _load_kb()
    combined_text = f"{crop_name} {symptoms}"

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        score = _score_entry(entry, crop_name, combined_text)
        if score > 0.1:  # exclude entries that only matched "general" baseline
            scored.append((score, entry))

    # Sort by score descending, then limit
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    results: list[KnowledgeEntry] = []
    for score, entry in top:
        results.append(
            KnowledgeEntry(
                id=entry["id"],
                crop=entry["crop"],
                topic=entry["topic"],
                content=entry["content"],
                source_title=entry["source_title"],
                source_url=entry.get("source_url"),
                severity=entry.get("severity", "unknown"),
                relevance_score=score,
            )
        )

    note = None
    if not results:
        note = (
            "No closely matching entries found in the local knowledge base for the "
            "reported crop and symptoms. Consider consulting a local agricultural extension service."
        )

    return ResearchResult(entries=results, is_demo=False, note=note)
