# Sequence Diagrams

## 1. End-to-End Evaluation Flow (Happy Path — Auto Pass)

```mermaid
sequenceDiagram
    autonumber
    participant QG as Question Generator
    participant API as Ingestion API
    participant KF as Kafka
    participant FE as Feature Extractor
    participant RS as Redis (Feature Store)
    participant T1 as Tier 1 (Rules)
    participant T2 as Tier 2 (ML Model)
    participant DR as Decision Router
    participant DB as Results DB
    participant MON as Monitoring

    QG->>API: POST /evaluate {question, source_doc, answer, metadata}
    API->>API: Validate input (Pydantic schema)
    API->>KF: Publish to evaluation topic
    API-->>QG: 202 Accepted {evaluation_id}

    KF->>FE: Consume message
    FE->>FE: Compute text features (length, grammar, readability)
    FE->>FE: Generate embeddings (sentence-transformers)
    FE->>FE: Compute semantic similarity, BLEU, ROUGE
    FE->>RS: Store feature vector (TTL: 24h)
    FE->>KF: Publish to scoring topic

    KF->>T1: Consume for rule-based evaluation
    T1->>RS: Fetch features
    T1->>T1: Apply rules (grammar OK, format OK, length OK)
    T1->>KF: Publish PASS to tier-2 topic

    KF->>T2: Consume for ML evaluation
    T2->>RS: Fetch feature vector
    T2->>T2: DeBERTa inference (per-dimension scores)
    T2->>T2: XGBoost scoring (engineered features)
    T2->>T2: Aggregate: score=82, confidence=0.94
    T2->>KF: Publish scores to decision topic

    KF->>DR: Consume scores
    DR->>DR: Apply thresholds (conf>0.9 AND score>75 → PASS)
    DR->>DB: Store result {PASS, score=82, confidence=0.94}
    DR->>MON: Emit metrics (latency, decision, scores)
    DR-->>API: Webhook/callback with result

    Note over QG,MON: Total latency: ~120ms (P50)
```


## 2. Uncertain Case — Escalation to LLM Judge + Human Review

```mermaid
sequenceDiagram
    autonumber
    participant T2 as Tier 2 (ML Model)
    participant KF as Kafka
    participant T3 as Tier 3 (LLM Judge)
    participant DR as Decision Router
    participant RQ as Review Queue
    participant UI as Review UI
    participant REV as Human Reviewer
    participant FC as Feedback Collector
    participant DB as Results DB
    participant MON as Monitoring

    T2->>T2: Score=55, Confidence=0.62
    T2->>KF: Publish to LLM-judge topic (low confidence)

    KF->>T3: Consume for LLM evaluation
    T3->>T3: Build evaluation prompt with rubric
    T3->>T3: Call LLM API (GPT-4/Claude)
    T3->>T3: Parse structured response
    T3->>T3: LLM score=48, explanation="Answer not fully supported"
    T3->>KF: Publish LLM scores to decision topic

    KF->>DR: Consume combined scores
    DR->>DR: ML=55, LLM=48, blended=51 → REVIEW
    DR->>RQ: Route to human review queue (priority: P2)
    DR->>DB: Store preliminary result {REVIEW, score=51}
    DR->>MON: Emit metrics (escalation count++)

    RQ->>UI: Push to reviewer dashboard
    UI->>REV: Display question + source + scores + explanation

    REV->>UI: Submit review {reject, clarity=2, groundedness=3, feedback="..."}
    UI->>FC: Store human judgment

    FC->>DB: Update result {REJECT, human_override=true}
    FC->>MON: Emit human review metrics
    FC->>KF: Publish feedback event (for training data)

    Note over T2,MON: Total latency: ~45min (includes human review wait time)
```


## 3. Feedback Loop — Model Retraining

```mermaid
sequenceDiagram
    autonumber
    participant FC as Feedback Collector
    participant DS as Dataset Store (DVC+S3)
    participant DRIFT as Drift Detector
    participant AF as Airflow
    participant TP as Training Pipeline
    participant MR as Model Registry (MLflow)
    participant GOLD as Gold Benchmark
    participant CANARY as Canary Deployment
    participant PROD as Production Model
    participant MON as Monitoring

    Note over FC,MON: Trigger: Drift detected OR 10K new labels OR monthly schedule

    DRIFT->>DRIFT: Detect concept drift (rolling window F1 drop)
    DRIFT->>AF: Trigger retraining DAG
    DRIFT->>MON: Alert: drift detected

    AF->>DS: Fetch latest labeled dataset
    DS->>AF: Return dataset v2.3 (DVC hash: abc123)
    AF->>TP: Launch training job (Ray cluster)

    TP->>TP: Data preprocessing + augmentation
    TP->>TP: Train DeBERTa (fine-tune on new data)
    TP->>TP: Train XGBoost (on engineered features)
    TP->>TP: Calibrate confidence scores (Platt scaling)
    TP->>TP: Evaluate on validation set

    TP->>GOLD: Run benchmark evaluation
    GOLD-->>TP: Metrics: F1=0.89, Precision=0.96, AUC=0.95

    alt Benchmark passes (beats production by >0.5%)
        TP->>MR: Register model v2.4 (status: staging)
        MR->>CANARY: Deploy to canary (5% traffic)
        
        loop 24-hour soak test
            CANARY->>MON: Emit canary metrics
            MON->>MON: Compare canary vs production
        end

        alt Canary metrics OK
            CANARY->>PROD: Promote to production (gradual rollout)
            PROD->>MR: Update status: production
            MR->>MON: Log deployment event
        else Canary metrics degraded
            CANARY->>MR: Rollback, mark as failed
            MR->>MON: Alert: canary failed, rolled back
        end
    else Benchmark fails
        TP->>MR: Log failed experiment
        TP->>MON: Alert: retraining did not improve model
    end

    Note over FC,MON: Cycle repeats continuously
```


## 4. Human Review — Disagreement Resolution

```mermaid
sequenceDiagram
    autonumber
    participant RQ as Review Queue
    participant R1 as Reviewer 1
    participant R2 as Reviewer 2
    participant R3 as Reviewer 3 (Tie-breaker)
    participant ADJ as Senior Adjudicator
    participant FC as Feedback Collector
    participant GOLD as Gold Dataset

    RQ->>R1: Assign question for review
    RQ->>R2: Assign same question (independent)

    R1->>FC: Submit: PASS (score: 72)
    R2->>FC: Submit: REJECT (score: 35)

    FC->>FC: Detect disagreement (PASS vs REJECT)
    FC->>RQ: Escalate to tie-breaker

    RQ->>R3: Assign for third review
    R3->>FC: Submit: REJECT (score: 40)

    FC->>FC: Majority vote: REJECT (2-1)
    FC->>FC: Flag for calibration (reviewer 1 outlier)

    alt High disagreement on specific dimension
        FC->>ADJ: Escalate to senior adjudicator
        ADJ->>FC: Final ruling + rationale
        FC->>GOLD: Add to gold dataset with expert label
    else Clear majority
        FC->>GOLD: Add to training set with majority label
    end

    FC->>FC: Update reviewer reliability scores
    FC->>FC: Log for inter-annotator agreement tracking

    Note over RQ,GOLD: Cohen's kappa monitored; retrain if < 0.7
```

## 5. Batch Evaluation Flow

```mermaid
sequenceDiagram
    autonumber
    participant CLIENT as Client System
    participant API as Batch API
    participant S3 as S3 Storage
    participant AF as Airflow
    participant EVAL as Eval Workers (Ray)
    participant DB as Results DB
    participant NF as Notification Service

    CLIENT->>API: POST /batch-evaluate {s3_path, callback_url}
    API->>API: Validate batch manifest
    API-->>CLIENT: 202 Accepted {batch_id, estimated_time}
    API->>S3: Verify input file exists
    API->>AF: Trigger batch evaluation DAG

    AF->>S3: Download input file (questions.jsonl)
    AF->>AF: Partition into chunks (1000 per chunk)
    
    par Parallel Evaluation
        AF->>EVAL: Chunk 1 (1000 questions)
        AF->>EVAL: Chunk 2 (1000 questions)
        AF->>EVAL: Chunk N (remaining)
    end

    EVAL->>EVAL: Feature extraction (batched)
    EVAL->>EVAL: Tier 1 + Tier 2 evaluation (batched GPU inference)
    EVAL->>EVAL: Tier 3 for uncertain cases (rate-limited)
    EVAL->>DB: Store results
    EVAL->>S3: Write results file (results.jsonl)

    AF->>AF: Aggregate batch metrics
    AF->>DB: Store batch summary
    AF->>NF: Send completion notification
    NF->>CLIENT: Callback {batch_id, status, results_path, summary}

    Note over CLIENT,NF: Batch of 100K questions: ~15 minutes
```

## Latency Breakdown

| Path | Steps | P50 Latency | P99 Latency |
|------|-------|-------------|-------------|
| Auto Pass (Tier 1+2) | Ingest → Features → Rules → ML → Decision | 80ms | 200ms |
| LLM Escalation | Above + LLM call | 1.5s | 3s |
| Human Review | Above + queue wait + review | 30min | 4hr |
| Batch (per question) | Bulk features → Bulk inference | 15ms | 50ms |
| Retraining cycle | Drift detect → Train → Deploy | 4hr | 8hr |
