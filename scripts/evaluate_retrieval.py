"""Compare baseline retrieval with local cross-encoder reranking."""

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
from rag.reranking import LocalCrossEncoderReranker, rerank_results
from rag.retrieval import KnowledgeRetriever

CASES_PATH = PROJECT_ROOT / "evaluation" / "retrieval_cases.json"


def summarize(
    ranked_sources: list[list[str]],
    relevant_sets: list[set[str]],
    unique_counts: list[int],
    *,
    label: str,
) -> None:
    recalls = [
        recall_at_k(sources, relevant, 5)
        for sources, relevant in zip(ranked_sources, relevant_sets, strict=True)
    ]
    mrr = mean_reciprocal_rank(ranked_sources, relevant_sets)

    print(f"=== {label} Summary ===")
    print(f"Recall@5:           {sum(recalls) / len(recalls):.3f}")
    print(f"MRR:                {mrr:.3f}")
    print(f"Avg unique sources: {sum(unique_counts) / len(unique_counts):.2f}")


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    retriever = KnowledgeRetriever()
    reranker = LocalCrossEncoderReranker()
    candidate_k = 10
    top_k = 5

    baseline_sources: list[list[str]] = []
    reranked_sources: list[list[str]] = []
    relevant_sets: list[set[str]] = []
    baseline_unique: list[int] = []
    reranked_unique: list[int] = []

    print(
        f"Evaluating {len(cases)} queries: "
        f"baseline top_k={top_k}, reranking candidates={candidate_k}\n"
    )

    for case in cases:
        relevant = set(case["relevant_sources"])
        candidates = retriever.retrieve(case["query"], top_k=candidate_k)
        baseline = candidates[:top_k]
        reranked = rerank_results(
            case["query"],
            candidates,
            reranker,
            top_k=top_k,
        )

        baseline_source_list = [result.source for result in baseline]
        reranked_source_list = [result.source for result in reranked]
        baseline_sources.append(baseline_source_list)
        reranked_sources.append(reranked_source_list)
        relevant_sets.append(relevant)
        baseline_unique.append(unique_source_count(baseline_source_list, top_k))
        reranked_unique.append(unique_source_count(reranked_source_list, top_k))

        baseline_recall = recall_at_k(baseline_source_list, relevant, top_k)
        reranked_recall = recall_at_k(reranked_source_list, relevant, top_k)

        print(
            f"[{case['id']}] baseline Recall@5={baseline_recall:.3f} | "
            f"reranked Recall@5={reranked_recall:.3f}"
        )
        print("  Baseline:")
        for rank, result in enumerate(baseline, start=1):
            marker = "*" if result.source in relevant else " "
            print(f"   {marker}{rank}. {result.score:.4f} | {result.source}")
        print("  Reranked:")
        for rank, result in enumerate(reranked, start=1):
            marker = "*" if result.source in relevant else " "
            print(f"   {marker}{rank}. {result.score:.4f} | {result.source}")
        print()

    summarize(
        baseline_sources,
        relevant_sets,
        baseline_unique,
        label="Baseline",
    )
    print()
    summarize(
        reranked_sources,
        relevant_sets,
        reranked_unique,
        label="Reranked",
    )


if __name__ == "__main__":
    main()
