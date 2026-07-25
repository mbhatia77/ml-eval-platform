# ML Evaluation Platform for Automatically Generated Assessment Questions

## Overview

An end-to-end ML-powered evaluation platform that automatically evaluates AI-generated assessment questions across multiple quality dimensions, routes uncertain cases to human reviewers, and continuously improves through feedback loops.

## Problem

A production AI pipeline generates thousands of assessment questions daily from enterprise documents. There is no automated way to measure quality or continuously improve the system. This platform solves that by providing:

- Multi-dimensional quality scoring (correctness, groundedness, relevance, clarity, etc.)
- Confidence-based routing (pass / review / reject)
- Human-in-the-loop for uncertain predictions
- Continuous improvement via feedback and retraining

## Project Structure

```
ml-eval-platform/
├── docs/                    # Design documents and specs
│   └── design-document.md   # Interview-style ML system design
├── diagrams/                # Architecture and sequence diagrams
│   ├── system-architecture.md
│   └── sequence-diagram.md
├── src/                     # Source code
│   ├── api/                 # REST API layer
│   ├── evaluation/          # Core evaluation engine
│   ├── features/            # Feature engineering
│   ├── models/              # Model definitions and registry
│   ├── human_review/        # Human-in-the-loop workflow
│   ├── pipeline/            # Data and inference pipelines
│   ├── monitoring/          # Metrics, drift detection, alerting
│   ├── training/            # Training and retraining pipelines
│   └── utils/               # Shared utilities
├── configs/                 # Configuration files
├── infrastructure/          # Docker, K8s, CI/CD
└── tests/                   # Unit and integration tests
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the evaluation API
python -m src.api.main

# Run evaluation on a batch
python -m src.pipeline.batch_evaluator --input questions.jsonl

# Run tests
pytest tests/
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Evaluator | Ensemble (Rules + ML + LLM) | Balance cost, accuracy, latency |
| Queue System | Kafka | High throughput, replay, ordering |
| Feature Store | Redis + PostgreSQL | Low-latency serving + historical |
| Human Review | Confidence thresholds | Route only uncertain cases |
| Model Registry | MLflow | Industry standard, versioning |
| Monitoring | Prometheus + Grafana | Real-time metrics, alerting |

## Architecture

See [System Architecture](diagrams/system-architecture.md) and [Sequence Diagram](diagrams/sequence-diagram.md) for detailed visual representations.

## Design Document

See [ML System Design Document](docs/design-document.md) for the complete interview-style design covering all architectural decisions, tradeoffs, and alternatives.
