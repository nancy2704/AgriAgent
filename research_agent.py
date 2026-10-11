"""
Agricultural Research Agent
Retrieves relevant information from the local curated knowledge base.
Clearly distinguishes retrieved facts from generated explanations.
Never invents citations.
"""
from __future__ import annotations

from models.schemas import FarmerInput, ResearchResult
from tools.agricultural_knowledge import search_knowledge_base


def run_research(farmer_input: FarmerInput, top_k: int = 3) -> ResearchResult:
    """
    Search the curated agricultural knowledge base for entries relevant
    to the farmer's reported crop and symptoms.

    All returned content is sourced directly from the knowledge base entries.
    No content is generated or inferred beyond what is stored.

    Args:
        farmer_input: Validated farmer problem submission.
        top_k:        Maximum number of knowledge base entries to return.

    Returns:
        ResearchResult containing matched KnowledgeEntry objects.
    """
    combined_symptoms = farmer_input.symptoms
    if farmer_input.additional_notes:
        combined_symptoms += " " + farmer_input.additional_notes

    result = search_knowledge_base(
        crop_name=farmer_input.crop_name,
        symptoms=combined_symptoms,
        top_k=top_k,
    )
    return result
