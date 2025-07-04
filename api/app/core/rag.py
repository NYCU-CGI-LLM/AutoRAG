"""
RAG core runner module.
This module provides functions to run retrieval, generation, and full RAG pipelines using BaseRunner/Runner.
"""
import yaml
import pandas as pd
import uuid as _uuid
import json

from app.core.rag_base import Runner
from app.schemas.rag import RetrieveResponse, GenerateResponse, RagResponse, RetrievedPassage
from typing import List, Optional


def run_retrieve(yaml_path: str, project_dir: str, query: str, top_k: int = 5, corpus_path: Optional[str] = None) -> RetrieveResponse:
    """
    Run retrieval-only stage: query expansion, retrieve, filter, rerank, augment, compress.
    """
    # Initialize runner and starting DataFrame
    runner = Runner.from_yaml(yaml_path, project_dir=project_dir)
    # Optionally override corpus DataFrame for retrieval nodes
    if corpus_path is not None:
        from autorag.nodes.retrieval.base import BaseRetrieval as _BaseRetrieval
        for inst in runner.module_instances:
            if isinstance(inst, _BaseRetrieval):
                inst.corpus_df = pd.read_parquet(corpus_path)
                break
    # Build initial previous_result DataFrame
    previous_result = pd.DataFrame({
        "qid": str(_uuid.uuid4()),
        "query": [query],
        "retrieval_gt": [[]],
        "generation_gt": [""],
    })
    # Manually run each module in the pipeline
    for module_instance, module_param in zip(runner.module_instances, runner.module_params):
        new_result = module_instance.pure(
            previous_result=previous_result,
            **module_param,
            top_k=top_k
        )
        # merge new columns
        dup_cols = previous_result.columns.intersection(new_result.columns)
        previous_result = pd.concat([
            previous_result.drop(columns=dup_cols),
            new_result
        ], axis=1)
    # Debug: print out all columns after pipeline
    print("Pipeline DataFrame columns:", previous_result.columns.tolist())
    # Extract retrieval outputs
    contents = previous_result["retrieved_contents"].tolist()[0]
    ids = previous_result["retrieved_ids"].tolist()[0]
    scores = previous_result["retrieve_scores"].tolist()[0]
    passages = [RetrievedPassage(content=c, doc_id=i, score=s)
                for c, i, s in zip(contents, ids, scores)]
    return RetrieveResponse(passages=passages)


def run_generate(
    yaml_path: str,
    project_dir: str,
    query: str,
    retrieved_passages: List[RetrievedPassage],
    result_column: str = "generated_texts",
) -> GenerateResponse:
    """
    Run generation-only stage: build prompt from retrieved passages and call the generator.
    """
    # Initialize pipeline runner
    runner = Runner.from_yaml(yaml_path, project_dir=project_dir)
    # Build initial DataFrame with retrieved_passages
    previous_result = pd.DataFrame({
        "qid": str(_uuid.uuid4()),
        "query": [query],
        "retrieval_gt": [[]],
        "generation_gt": [""],
        "retrieved_contents": [[p.content for p in retrieved_passages]],
        "retrieved_ids": [[p.doc_id for p in retrieved_passages]],
        "retrieve_scores": [[p.score for p in retrieved_passages]],
    })
    # Execute only generation modules (skip first retrieval module)
    for module_instance, module_param in zip(
        runner.module_instances[1:], runner.module_params[1:]
    ):
        new_result = module_instance.pure(
            previous_result=previous_result,
            **module_param,
        )
        dup_cols = previous_result.columns.intersection(new_result.columns)
        previous_result = pd.concat(
            [previous_result.drop(columns=dup_cols), new_result], axis=1
        )
    # Extract generation output
    answer = previous_result[result_column].tolist()[0]
    return GenerateResponse(answer=answer)


def run_full_rag(yaml_path: str, project_dir: str, query: str, top_k: int = 5, result_column: str = "generated_texts", corpus_path: Optional[str] = None) -> RagResponse:
    """
    Run full RAG pipeline: retrieve then generate.
    """
    retrieve_response = run_retrieve(yaml_path, project_dir, query, top_k, corpus_path)
    generate_response = run_generate(yaml_path, project_dir, query, retrieve_response.passages, result_column)
    return RagResponse(result=generate_response.answer, retrieved_passage=retrieve_response.passages)


__all__ = ["run_retrieve", "run_generate", "run_full_rag"]

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple CLI for RAG operations")
    parser.add_argument("--yaml_path", "-y", required=True, help="Path to extracted pipeline YAML file")
    parser.add_argument("--project_dir", "-p", required=True, help="Project directory containing resources")
    parser.add_argument("--query", "-q", required=True, help="Query string to process")
    parser.add_argument(
        "--mode", "-m",
        choices=["retrieve", "generate", "full"],
        default="full",
        help="Operation mode: retrieve, generate, or full"
    )
    parser.add_argument("--top_k", type=int, default=5, help="Number of passages to retrieve")
    parser.add_argument(
        "--result_column", default="generated_texts",
        help="Result column name for generation"
    )
    parser.add_argument(
        "--corpus_path", "-c",
        default=None,
        help="Optional path to custom corpus parquet file to override default data/corpus.parquet"
    )
    args = parser.parse_args()

    if args.mode == "retrieve":
        response = run_retrieve(
            args.yaml_path,
            args.project_dir,
            args.query,
            args.top_k,
            args.corpus_path
        )
    elif args.mode == "generate":
        retrieved = run_retrieve(
            args.yaml_path,
            args.project_dir,
            args.query,
            args.top_k,
            args.corpus_path
        )
        response = run_generate(
            args.yaml_path,
            args.project_dir,
            args.query,
            retrieved.passages,
            args.result_column
        )
    else:
        response = run_full_rag(
            args.yaml_path,
            args.project_dir,
            args.query,
            args.top_k,
            args.result_column,
            args.corpus_path
        )

    # Print JSON-formatted result
    print(json.dumps(response.model_dump(), indent=2)) 