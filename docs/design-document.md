# ML Evaluation Platform — System Design Document

## Executive Summary

This document presents the complete ML system design for an **Automated Assessment Question Evaluation Platform**. The platform evaluates AI-generated questions across 10 quality dimensions, assigns confidence-based routing decisions (Pass/Review/Reject), and continuously improves through human feedback loops.

This design addresses enterprise-scale requirements: millions of evaluations per day, low latency, high precision, and cost-effective inference.

---

## 1. Problem Decomposition

### Clarifying Questions & Assumptions

| Question | Assumption |
|----------|------------|
| What is acceptable evaluation latency? | < 500ms p99 for real-time; batch can be minutes |
| What is the acceptable false acceptance rate? | < 2% (high precision required) |
| How many human reviewers are available? | 50-100 reviewers, 8-hour shifts |
| What languages are supported initially? | English first, then multilingual |
| What is the cost budget per evaluation? | < $0.01 per question for automated eval |
| Are source documents always available? | Yes, source doc is always paired with question |
| What is the expected quality distribution? | ~70% pass, ~20% review, ~10% reject |
| Is there existing labeled data? | Limited (~5K labeled examples initially) |

---

## 2. System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ML EVALUATION PLATFORM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐              │
│  │ Question │───▶│  Evaluation  │───▶│  Decision   │              │
│  │ Ingestion│    │   Engine     │    │   Router    │              │
│  └──────────┘    └──────────────┘    └─────────────┘              │
│       │                │                    │                       │
│       ▼                ▼                    ▼                       │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐              │
│  │ Feature  │    │    Model     │    │   Human     │              │
│  │  Store   │    │   Registry   │    │   Review    │              │
│  └──────────┘    └──────────────┘    └─────────────┘              │
│       │                │                    │                       │
│       ▼                ▼                    ▼                       │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐              │
│  │ Training │    │  Monitoring  │    │  Feedback   │              │
│  │ Pipeline │    │  & Alerting  │    │    Loop     │              │
│  └──────────┘    └──────────────┘    └─────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Service Breakdown

| Service | Responsibility | Technology |
|---------|---------------|------------|
| Ingestion Service | Receive questions from generation pipeline | FastAPI + Kafka |
| Feature Service | Compute and cache evaluation features | Python + Redis |
| Evaluation Engine | Run multi-dimensional scoring | Python + PyTorch |
| Decision Router | Apply thresholds, route to pass/review/reject | Rule engine |
| Human Review UI | Present questions to reviewers | React + WebSocket |
| Feedback Collector | Aggregate human judgments | PostgreSQL |
| Training Pipeline | Retrain models on new data | Airflow + MLflow |
| Model Registry | Version and deploy models | MLflow |
| Monitoring | Track metrics, detect drift | Prometheus + Grafana |
| Dashboard | Business metrics and analytics | Grafana + custom UI |

### Architecture Decisions

**Decision 1: Event-Driven Architecture with Kafka**

- **Why:** Decouples generation from evaluation; handles burst traffic; enables replay for debugging
- **Alternative:** Synchronous REST calls between services
- **Advantage:** Back-pressure handling, independent scaling, fault tolerance
- **Disadvantage:** Added complexity, eventual consistency
- **Cost:** Kafka cluster ~$2K/month at scale

**Decision 2: Tiered Evaluation Strategy**

- **Why:** Not all dimensions need expensive LLM calls. Use cheap checks first, escalate only when needed.
- **Tier 1 (< 10ms):** Rule-based checks (grammar, length, format)
- **Tier 2 (< 50ms):** ML model scoring (trained classifier)
- **Tier 3 (< 500ms):** LLM-as-judge (only for uncertain cases)
- **Alternative:** Run all evaluations through LLM
- **Advantage:** 80% cost reduction, 90% latency reduction for clear cases
- **Disadvantage:** Tier 1/2 may miss nuanced quality issues
- **Cost:** Blended cost ~$0.003/question vs $0.02/question (LLM-only)

**Decision 3: Microservices over Monolith**

- **Why:** Independent scaling (evaluation engine needs GPU, ingestion does not), independent deployment
- **Alternative:** Monolithic application
- **Advantage:** Scale evaluation independently, deploy metrics without touching core
- **Disadvantage:** Network overhead, distributed system complexity
- **Cost:** Higher infrastructure but offset by efficient resource utilization

---

## 3. Data Pipeline

### Data Collection Strategy

```
Source Documents ──▶ Question Generator ──▶ Raw Questions
                                                │
                                                ▼
                                    ┌─────────────────────┐
                                    │  Evaluation Input    │
                                    │  - source_doc        │
                                    │  - question          │
                                    │  - expected_answer   │
                                    │  - metadata          │
                                    └─────────────────────┘
                                                │
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                   ▼
                     Automated Eval      Human Review         Gold Dataset
                              │                 │                   │
                              └─────────────────┼───────────────────┘
                                                ▼
                                        Training Data Store
```

### Labeling Strategy

| Phase | Approach | Volume | Purpose |
|-------|----------|--------|---------|
| Bootstrap | Expert annotation of seed set | 5,000 | Initial model training |
| Growth | Active learning + human review | 50,000 | Model improvement |
| Steady State | Disagreement sampling | Ongoing | Continuous calibration |

**Gold Dataset Creation:**
1. Sample stratified by domain, difficulty, document type
2. Three independent annotators per question
3. Majority vote with adjudication for disagreements
4. Inter-annotator agreement threshold: Cohen's kappa > 0.7
5. Refresh quarterly with new domains and edge cases

**Data Versioning:**
- DVC (Data Version Control) for dataset snapshots
- Every training run linked to specific data version
- Schema validation on ingest (Pydantic models)
- Data lineage tracking from source doc to evaluation result

**Data Quality Controls:**
- Automated schema validation
- Distribution monitoring (alert on class imbalance shifts)
- Deduplication pipeline
- PII detection and scrubbing
- Staleness checks on source documents

---

## 4. Feature Engineering

### Feature Categories

#### Text Quality Features (Computed in < 5ms)
| Feature | Description | Library |
|---------|-------------|---------|
| `question_length` | Character and word count | Built-in |
| `readability_score` | Flesch-Kincaid grade level | textstat |
| `grammar_errors` | Count of grammatical issues | language-tool |
| `sentence_count` | Structural complexity | spaCy |
| `question_type` | Classification (who/what/why/how) | Regex + spaCy |
| `has_correct_punctuation` | Ends with ?, proper formatting | Regex |

#### Semantic Features (Computed in < 50ms)
| Feature | Description | Library |
|---------|-------------|---------|
| `source_similarity` | Cosine similarity to source doc | sentence-transformers |
| `answer_consistency` | Does answer match question intent | Custom model |
| `embedding_distance` | Distance from source in embedding space | FAISS |
| `topic_alignment` | Question topic vs document topic | BERTopic |
| `entity_overlap` | Named entities shared with source | spaCy NER |

#### Reference-Based Features (Computed in < 100ms)
| Feature | Description | Library |
|---------|-------------|---------|
| `bleu_score` | N-gram overlap with source | sacrebleu |
| `rouge_score` | Recall-oriented overlap | rouge-score |
| `bertscore` | Contextual embedding similarity | bert-score |
| `faithfulness` | Factual consistency with source | Custom NLI model |

#### Safety Features (Computed in < 50ms)
| Feature | Description | Library |
|---------|-------------|---------|
| `toxicity_score` | Offensive/harmful content detection | Detoxify |
| `bias_indicators` | Gender/race/age bias detection | Custom classifier |
| `pii_detected` | Personal information leakage | Presidio |

#### Duplicate Detection Features (Computed in < 20ms)
| Feature | Description | Library |
|---------|-------------|---------|
| `min_hash_signature` | Approximate duplicate detection | datasketch |
| `semantic_dedup_score` | Embedding-based dedup | FAISS |
| `exact_match_ratio` | Character-level overlap | difflib |

### Feature Store Architecture

```
┌─────────────────────────────────────────────┐
│              Feature Store                    │
├─────────────────────────────────────────────┤
│                                             │
│  Online Store (Redis)                       │
│  - Pre-computed features for active docs    │
│  - TTL: 24 hours                            │
│  - Latency: < 5ms                           │
│                                             │
│  Offline Store (PostgreSQL + Parquet)       │
│  - Historical features for training         │
│  - Point-in-time correct joins              │
│  - Partitioned by date                      │
│                                             │
│  Computation Engine (Ray)                   │
│  - Distributed feature computation          │
│  - Batch and streaming modes               │
│  - GPU-accelerated embeddings              │
│                                             │
└─────────────────────────────────────────────┘
```

**Tradeoff:** Redis for online serving (fast but expensive at scale) vs. PostgreSQL for training (slow but cheap and queryable). We use Redis for the hot path and precompute features during ingestion to avoid latency at evaluation time.

---

## 5. Model Design

### Approach Comparison

| Approach | Accuracy | Latency | Cost/Question | Maintainability | Cold Start |
|----------|----------|---------|---------------|-----------------|------------|
| Rule-Based | Low (60%) | < 5ms | ~$0.0001 | High | Immediate |
| Traditional ML (XGBoost) | Medium (78%) | < 10ms | ~$0.0005 | High | Needs data |
| Fine-tuned Transformer | High (88%) | < 50ms | ~$0.002 | Medium | Needs data |
| LLM-as-Judge (GPT-4) | Very High (92%) | < 2s | ~$0.02 | Low | Immediate |
| **Ensemble (Chosen)** | **High (90%)** | **< 100ms** | **~$0.003** | **Medium** | **Partial** |

### Chosen Architecture: Tiered Ensemble

```
Input Question + Source Doc
         │
         ▼
┌─────────────────────┐
│  Tier 1: Rule-Based │  ◀── Catches obvious failures (grammar, format, length)
│  (Gate: 15% reject) │      Cost: ~$0.0001 | Latency: 5ms
└─────────┬───────────┘
          │ (passes ~85%)
          ▼
┌─────────────────────┐
│  Tier 2: ML Model   │  ◀── Fine-tuned DeBERTa + XGBoost on features
│  (Score + Conf)     │      Cost: ~$0.002 | Latency: 40ms
└─────────┬───────────┘
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
  PASS  REVIEW  REJECT    (Based on confidence thresholds)
          │
          ▼ (only ~10% reach here)
┌─────────────────────┐
│  Tier 3: LLM Judge  │  ◀── GPT-4 / Claude for nuanced evaluation
│  (Explanation)       │      Cost: ~$0.02 | Latency: 1-2s
└─────────────────────┘
```

### Why Ensemble Over Single Model

- **Cost optimization:** 85% of questions resolved by cheap Tier 1+2 ($0.002 avg)
- **Latency:** Only uncertain cases hit slow LLM path
- **Accuracy:** LLM catches what ML misses, but only when needed
- **Graceful degradation:** If LLM is down, Tier 2 still provides reasonable scores
- **Explainability:** Each tier provides different explanation types

### Model Details

**Tier 2 Architecture:**
```
Input: [question, source_doc, expected_answer, metadata]
   │
   ├──▶ DeBERTa-v3-base (fine-tuned)
   │         │
   │         ▼
   │    [CLS embedding] ──▶ Per-dimension scores (10 heads)
   │
   ├──▶ Feature Extractor
   │         │
   │         ▼
   │    [engineered features] ──▶ XGBoost (calibrated probabilities)
   │
   └──▶ Aggregator
              │
              ▼
         Final Score + Confidence + Decision
```

**Training Strategy:**
- Pre-train on general NLI + quality assessment data
- Fine-tune on domain-specific labeled data
- Calibrate with Platt scaling for reliable confidence scores
- Multi-task learning: all 10 dimensions share encoder, separate heads

**Tradeoff:** DeBERTa-v3-base (86M params) over larger models because:
- Fits on single GPU for inference
- Batched inference: 200+ questions/second
- Fine-tuning feasible with 5K examples
- Accuracy within 3% of DeBERTa-large at 4x lower cost

---

## 6. Human-in-the-Loop Design

### Confidence-Based Routing

```
Score + Confidence ──▶ Decision Matrix:

┌────────────────────────────────────────────────┐
│  Confidence > 0.9 AND Score > 75  ──▶  PASS   │
│  Confidence > 0.9 AND Score < 30  ──▶  REJECT │
│  Confidence < 0.7                 ──▶  REVIEW │
│  0.7 < Confidence < 0.9          ──▶  Tier 3  │
│  Score between 30-75 (any conf)   ──▶  REVIEW │
└────────────────────────────────────────────────┘
```

### Escalation Rules

| Condition | Action | Priority |
|-----------|--------|----------|
| Safety flag triggered | Immediate human review | P0 |
| Model confidence < 0.5 | Senior reviewer | P1 |
| New domain (no training data) | Domain expert review | P1 |
| Disagreement with Tier 3 | Adjudication panel | P2 |
| Random sample (5%) | Quality audit | P3 |

### Sampling Strategy

- **Uncertainty sampling:** Route lowest-confidence predictions for labeling
- **Stratified sampling:** Ensure all domains represented in review queue
- **Adversarial sampling:** Prioritize questions where model disagrees with rules
- **Random sampling:** 5% baseline for unbiased quality estimation

### Reviewer Workflow

1. Reviewer sees: question, source doc, expected answer, model scores, explanation
2. Reviewer provides: pass/reject decision + per-dimension ratings + free-text feedback
3. Time limit: 60 seconds per question (prevents overthinking)
4. Minimum 3 reviews for gold dataset additions

### Disagreement Handling

- Two reviewers agree → Accept as ground truth
- Two reviewers disagree → Third reviewer breaks tie
- Three-way disagreement → Senior adjudicator + add to calibration set
- Systematic disagreement on dimension → Retrain dimension-specific model

### Gold Benchmark Maintenance

- Initial: 2,000 expert-labeled questions across domains
- Growth: 500 new gold examples/month from high-agreement reviews
- Refresh: Quarterly audit, remove stale examples
- Usage: Model evaluation, reviewer calibration, regression testing

---

## 7. Evaluation Metrics

### Offline Metrics (Model Performance)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Precision (reject class) | > 95% | Of predicted rejects, % actually bad |
| Recall (reject class) | > 85% | Of actually bad, % caught |
| F1 (overall) | > 88% | Harmonic mean across classes |
| ROC-AUC | > 0.94 | Discrimination ability |
| Calibration Error (ECE) | < 0.05 | Confidence reliability |
| Per-dimension correlation | > 0.8 | Agreement with human per metric |

### Online Metrics (Production Performance)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Human acceptance rate | > 92% | % of PASS decisions humans agree with |
| False acceptance rate | < 2% | Bad questions that slip through |
| Review-to-total ratio | < 15% | Efficiency of automation |
| Reviewer throughput | > 40/hour | Questions reviewed per hour |
| Customer satisfaction (CSAT) | > 4.2/5 | End-user quality perception |
| Mean time to evaluate | < 200ms | P50 latency |
| Cost per evaluation | < $0.005 | Blended cost across tiers |
| Model agreement with LLM | > 85% | Tier 2 vs Tier 3 alignment |

### Business Metrics

| Metric | Description |
|--------|-------------|
| Questions approved/day | Throughput of the system |
| Quality improvement rate | Month-over-month score improvement |
| Reviewer utilization | % of reviewer time spent on truly ambiguous cases |
| Cost savings vs. all-human | $ saved compared to manual review |
| Time to first evaluation | Latency from generation to score available |

---

## 8. MLOps

### Experiment Tracking

- **Tool:** MLflow Tracking Server
- **What's logged:** Hyperparameters, metrics, artifacts, data version, code version
- **Comparison:** Side-by-side experiment comparison dashboard
- **Naming convention:** `{model_type}_{data_version}_{date}_{experiment_id}`

### Dataset Versioning

- **Tool:** DVC (Data Version Control) + S3
- **Strategy:** Immutable snapshots, linked to Git commits
- **Schema:** Enforced via Pydantic models; migration scripts for schema changes
- **Retention:** Keep all versions; archive after 1 year

### Prompt Versioning (for LLM-as-Judge)

- **Storage:** Git-tracked prompt templates with semantic versioning
- **A/B testing:** Run multiple prompt versions in parallel, compare with gold set
- **Rollback:** Instant rollback to previous prompt version via feature flag
- **Evaluation:** Every prompt change evaluated on gold benchmark before deployment

### CI/CD Pipeline

```
Code Push ──▶ Unit Tests ──▶ Integration Tests ──▶ Model Tests ──▶ Deploy
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │ Benchmark Suite  │
                                              │ - Gold set eval  │
                                              │ - Latency check  │
                                              │ - Cost estimate  │
                                              │ - Bias audit     │
                                              └─────────────────┘
                                                        │
                                                        ▼
                                              Pass? ──▶ Canary Deploy (5%)
                                                        │
                                                        ▼ (24h soak)
                                              Metrics OK? ──▶ Full Rollout
```

### Model Registry

| Field | Description |
|-------|-------------|
| Model version | Semantic version (major.minor.patch) |
| Training data version | DVC hash of training set |
| Metrics on gold set | All offline metrics at registration time |
| Deployment status | staging / canary / production / retired |
| Owner | Team responsible for model |
| Approval | Required sign-off before production |

### Canary Deployments

- Shadow mode: New model scores alongside production, no routing impact
- Canary: 5% traffic to new model, compare metrics
- Graduated rollout: 5% → 25% → 50% → 100% over 48 hours
- Automatic rollback if: precision drops > 2%, latency increases > 50%, error rate > 1%

### Drift Detection

| Drift Type | Detection Method | Action |
|------------|-----------------|--------|
| Data drift | KL-divergence on feature distributions | Alert + investigate |
| Concept drift | Performance degradation on rolling window | Trigger retraining |
| Label drift | Human review acceptance rate change | Recalibrate thresholds |
| Prediction drift | Score distribution shift | Alert + A/B test |

### Retraining Strategy

- **Trigger:** Concept drift detected OR 10,000 new labeled examples OR monthly schedule
- **Process:** Automated pipeline: data prep → train → evaluate → register → canary
- **Validation:** Must beat current production model on gold set by > 0.5% F1
- **Rollback:** Automated if production metrics degrade within 24h

---

## 9. Scaling Design

### Target Scale

- 5 million questions/day peak
- 60 questions/second sustained
- 200 questions/second burst
- P99 latency < 500ms
- 99.9% availability

### Scaling Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │  API Pod 1 │ │  API Pod 2 │ │  API Pod N │  (Auto-scaled)
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                    ┌─────────────────┐
                    │     Kafka       │  (Partitioned by domain)
                    │   (32 parts)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ Eval Pod 1 │ │ Eval Pod 2 │ │ Eval Pod N │  (GPU-backed)
       │   (GPU)    │ │   (GPU)    │ │   (GPU)    │
       └────────────┘ └────────────┘ └────────────┘
```

### Scaling Strategies

| Component | Strategy | Details |
|-----------|----------|---------|
| API Layer | Horizontal Pod Autoscaler | CPU-based, 2-20 pods |
| Kafka | Partition by domain | 32 partitions, 3x replication |
| Eval Engine | GPU autoscaling | Based on queue depth |
| Feature Store | Redis Cluster | 6 nodes, read replicas |
| LLM Calls | Rate limiting + queue | Token bucket, retry with backoff |
| Database | Read replicas + sharding | Shard by tenant/domain |

### Multi-Language Support

- Embedding models: multilingual sentence-transformers (supports 100+ languages)
- Grammar checking: language-specific models loaded on demand
- LLM evaluation: language-aware prompts
- Feature store: language as partition key for cache efficiency

### Fault Tolerance

| Failure Mode | Mitigation |
|--------------|-----------|
| Eval pod crash | Kafka retries, consumer group rebalance |
| Redis failure | Fallback to real-time computation (degraded latency) |
| LLM provider down | Circuit breaker, fallback to Tier 2 only |
| Kafka down | In-memory buffer (5 min), alert, write to dead letter queue |
| Database failure | Read from replica, write buffer |
| Full system overload | Graceful degradation: skip Tier 3, increase REVIEW threshold |

### Caching Strategy

- **L1 Cache (in-process):** LRU cache for frequently seen source doc embeddings
- **L2 Cache (Redis):** Feature vectors, TTL 24h, ~90% hit rate
- **L3 Cache (CDN):** Static model artifacts, evaluation rubrics
- **Invalidation:** Event-driven on source doc update

### Queueing

- **Primary:** Kafka for evaluation pipeline (high throughput, ordering)
- **Secondary:** Redis Streams for human review queue (priority ordering)
- **Dead Letter:** S3 for failed evaluations (replay capability)
- **Backpressure:** Consumer lag monitoring, auto-scale on threshold

---

## 10. Tradeoffs Summary

### Key Design Decisions

| Decision | Chosen | Alternative | Why |
|----------|--------|-------------|-----|
| Architecture | Microservices + Events | Monolith | Independent scaling, team ownership |
| Primary Model | DeBERTa-v3-base ensemble | GPT-4 only | 10x cheaper, 20x faster, comparable accuracy |
| Queue | Kafka | RabbitMQ/SQS | Replay, ordering, high throughput |
| Feature Store | Redis + PostgreSQL | Feast/Tecton | Simpler ops, sufficient for our scale |
| Orchestration | Kubernetes | ECS/Lambda | GPU support, autoscaling, portable |
| Experiment Tracking | MLflow | W&B | Self-hosted, no data egress, OSS |
| LLM Provider | Multi-provider (OpenAI + Anthropic) | Single provider | Redundancy, cost optimization |
| Human Review | Custom UI | Label Studio | Domain-specific workflow needs |

### Cost Analysis

| Component | Monthly Cost (at scale) | Notes |
|-----------|------------------------|-------|
| GPU Inference (Tier 2) | $8,000 | 4x A100 GPUs, batched |
| LLM API (Tier 3) | $15,000 | Only 10% of traffic |
| Kafka Cluster | $2,000 | Managed service |
| Redis Cluster | $3,000 | Feature store |
| PostgreSQL | $1,500 | Managed RDS |
| Kubernetes | $5,000 | Control plane + nodes |
| Human Reviewers | $40,000 | 50 reviewers, part-time |
| MLflow/Monitoring | $1,000 | Self-hosted |
| **Total** | **~$75,500/month** | |
| **Cost per evaluation** | **~$0.005** | At 5M questions/day |

**vs. All-Human Review:** ~$500K/month (200 full-time reviewers)
**Savings:** ~85% cost reduction with comparable quality

### Operational Complexity

| Aspect | Complexity | Mitigation |
|--------|-----------|-----------|
| Multi-model serving | High | Standardized inference container |
| Feature pipeline | Medium | Batch + streaming unified (Ray) |
| Data labeling | Medium | Semi-automated with active learning |
| Monitoring | Medium | Standardized dashboards, PagerDuty |
| LLM prompt management | Low | Git-tracked, A/B tested |
| Retraining | Low | Fully automated pipeline |

---

## 11. Future Improvements

### Phase 2 (3-6 months)

1. **Active Learning Pipeline**
   - Prioritize labeling of most informative examples
   - Expected: 30% reduction in labeling cost for same model improvement

2. **Domain-Specific Evaluators**
   - Specialized models for medical, legal, technical domains
   - Transfer learning from general model
   - Expected: 5-8% accuracy improvement per domain

3. **Multi-Agent Evaluation**
   - Multiple LLM judges with different prompts
   - Voting mechanism for robustness
   - Expected: 3% reduction in false acceptance rate

### Phase 3 (6-12 months)

4. **RLHF for Evaluation Model**
   - Train reward model from human preferences
   - Align evaluation model with human judgment
   - Expected: Better calibration on subjective dimensions

5. **Continuous Prompt Optimization**
   - Automated prompt search (DSPy-style)
   - Optimize Tier 3 prompts for accuracy and cost
   - Expected: 20% cost reduction on LLM calls

6. **Adaptive Evaluation**
   - Dynamically adjust evaluation depth based on question complexity
   - Simple questions: fewer features needed
   - Expected: 40% latency reduction for easy cases

### Phase 4 (12+ months)

7. **Self-Improving Generation**
   - Feed evaluation signals back to question generator
   - Reduce bad question generation at source
   - Expected: 50% reduction in reject rate over time

8. **Federated Evaluation**
   - Evaluation models trained across tenants without sharing data
   - Privacy-preserving improvement
   - Expected: Better generalization for new tenants

---

## 12. Interview Discussion Points

### What I Would Ask the Interviewer

1. "What's the current false acceptance rate you're seeing with manual review?"
2. "Are there regulatory requirements around question quality in any domains?"
3. "How quickly does the question generation model change? (Affects drift)"
4. "Is there budget for GPU infrastructure or should we be cloud-API only?"
5. "What's the reviewer pool — internal employees or crowdsourced?"

### Key Principles Demonstrated

- **Start simple, iterate:** Begin with rules + small model, add complexity as data grows
- **Measure everything:** You can't improve what you don't measure
- **Human-AI partnership:** Humans handle ambiguity, AI handles volume
- **Cost-aware design:** Not every question needs expensive evaluation
- **Feedback loops:** Every human decision becomes training data
- **Graceful degradation:** System works at reduced capacity even with component failures

### What Makes This Design Production-Ready

1. Observable: Every prediction logged with explanation
2. Recoverable: Kafka replay, model rollback, dead letter queues
3. Testable: Gold benchmark, shadow mode, canary deployment
4. Evolvable: New metrics plug in without architecture changes
5. Economical: Tiered approach minimizes cost at scale
