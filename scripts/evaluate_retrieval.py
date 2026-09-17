"""Evaluate baseline semantic retrieval against the SentinelOps test set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.retrieval_metrics import (
    mean_reciprocal_rank,
    recall_at_k,
    unique_source_count,
)
from rag.retrieval import KnowledgeRetriever

CASES_PATH = PROJECT_ROOT / "evaluation" / "retrieval_cases.json"


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    retriever = KnowledgeRetriever()
    top_k = 5

    ranked_sources: list[list[str]] = []
    relevant_sets: list[set[str]] = []
    recalls: list[float] = []
    unique_counts: list[int] = []

    print(f"Evaluating {len(cases)} queries with top_k={top_k}\n")

    for case in cases:
        relevant = set(case["relevant_sources"])
        results = retriever.retrieve(case["query"], top_k=top_k)
        sources = [result.source for result in results]
        ranked_sources.append(sources)
        relevant_sets.append(relevant)
        recalls.append(recall_at_k(sources, relevant, top_k))
        unique_counts.append(unique_source_count(sources, top_k))

        print(
            f"[{case['id']}] Recall@5={recalls[-1]:.3f} | "
            f"unique_sources={unique_counts[-1]}"
        )
        for rank, result in enumerate(results, start=1):
            marker = "*" if result.source in relevant else " "
            print(f"  {marker}{rank}. {result.score:.4f} | {result.source}")
        print()

    mrr = mean_reciprocal_rank(ranked_sources, relevant_sets)
    print("=== Baseline Summary ===")
    print(f"Recall@5:           {sum(recalls) / len(recalls):.3f}")
    print(f"MRR:                {mrr:.3f}")
    print(f"Avg unique sources: {sum(unique_counts) / len(unique_counts):.2f}")


if __name__ == "__main__":
    main()
