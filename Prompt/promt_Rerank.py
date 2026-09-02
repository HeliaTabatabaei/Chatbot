import json


RERANK_SYSTEM_PROMPT = """You are a technical document reranker. Your job is to score relevance on a scale of 0.0 to 1.0.

Instructions:
- 1.0: The chunk contains the exact answer, error code explanation, or step-by-step solution.
- 0.8-0.9: Highly relevant. Provides critical context or strong supporting evidence for the answer.
- 0.5: Marginally relevant. Contains the right topic but lacks specific actionable details.
- 0.0-0.3: Irrelevant. Wrong device, wrong topic, or gibberish.

Rules:
- You MUST score every candidate.
- Return ONLY valid JSON array: [{"id": "...", "score": ...}]
- Do not add explanations."""


def build_rerank_user_prompt(
        original_query: str,
        rewritten_query: str,
        candidates: list[dict],
    ) -> str:
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        return (
            f"Original User Query:\n{original_query}\n\n"
            f"Rewritten/Target Query:\n{rewritten_query}\n\n"
            f"Results to Score:\n{candidates_json}\n\n"
            f"Return exactly {len(candidates)} JSON items. One score for each ID."
        )
