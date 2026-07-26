"""Batch evaluation pipeline for processing large question sets.

Processes JSONL files of questions in parallel using Ray for
distributed computation. Designed for offline/batch workloads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncIterator

from src.evaluation.engine import EvaluationEngine
from src.features.extractor import FeatureExtractor
from src.utils.config import get_config
from src.utils.models import EvaluationInput

logger = logging.getLogger(__name__)


class BatchEvaluator:
    """
    Processes batch evaluation jobs.

    Input: JSONL file where each line is an EvaluationInput
    Output: JSONL file with EvaluationResult for each question

    Supports parallel processing via chunked execution.
    """

    def __init__(self, chunk_size: int = 1000):
        self.config = get_config()
        self.chunk_size = chunk_size
        self.feature_extractor = FeatureExtractor()
        self.evaluation_engine = EvaluationEngine(self.config)

    async def process_file(self, input_path: str, output_path: str) -> dict:
        """
        Process an entire JSONL file of questions.

        Returns summary statistics.
        """
        results = {
            "total": 0,
            "passed": 0,
            "reviewed": 0,
            "rejected": 0,
            "errors": 0,
        }

        input_file = Path(input_path)
        output_file = Path(output_path)

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        with open(input_file, "r") as fin, open(output_file, "w") as fout:
            async for result in self._process_lines(fin):
                fout.write(json.dumps(result) + "\n")
                results["total"] += 1

                if "error" in result:
                    results["errors"] += 1
                else:
                    decision = result.get("decision", "review")
                    results[f"{decision}ed" if decision == "review" else f"{decision}ed"] = (
                        results.get(f"{decision}ed", 0) + 1
                    )

        logger.info(f"Batch complete: {results}")
        return results

    async def _process_lines(self, file_handle) -> AsyncIterator[dict]:
        """Process lines from the input file."""
        for line in file_handle:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                input = EvaluationInput(**data)

                # Extract features
                features = await self.feature_extractor.extract(input)

                # Evaluate
                result = await self.evaluation_engine.evaluate(input, features)

                yield result.model_dump(mode="json")

            except Exception as e:
                logger.error(f"Error processing line: {e}")
                yield {"error": str(e), "input": line[:200]}


def main():
    """CLI entry point for batch evaluation."""
    parser = argparse.ArgumentParser(description="Batch question evaluation")
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--output", default="results.jsonl", help="Output path")
    parser.add_argument("--chunk-size", type=int, default=1000)
    args = parser.parse_args()

    evaluator = BatchEvaluator(chunk_size=args.chunk_size)
    results = asyncio.run(evaluator.process_file(args.input, args.output))
    print(f"Batch evaluation complete: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    main()
