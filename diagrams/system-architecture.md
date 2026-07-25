# System Architecture Diagram

## ML Evaluation Platform — Complete System Architecture

```mermaid
graph TB
    %% External Sources
    subgraph Sources["Document Sources"]
        SD[Enterprise Documents]
        MN[Manuals & Regulations]
        KB[Knowledge Bases]
    end

    %% Question Generation Pipeline
    subgraph GenPipeline["Question Generation Pipeline"]
        QG[Question Generator<br/>LLM-based]
        PT[Prompt Templates<br/>Versioned]
        GM[Generation Models<br/>GPT-4 / Claude / Llama]
    end

    %% Ingestion Layer
    subgraph Ingestion["Ingestion Layer"]
        API[REST API<br/>FastAPI]
        LB[Load Balancer<br/>NGINX/ALB]
        VAL[Input Validator<br/>Pydantic]
    end

    %% Message Queue
    subgraph Queue["Event Streaming"]
        KF[Apache Kafka<br/>32 Partitions]
        DLQ[Dead Letter Queue<br/>S3]
    end

    %% Feature Engineering
    subgraph Features["Feature Engineering"]
        FE[Feature Extractor<br/>Ray Workers]
        EMB[Embedding Service<br/>sentence-transformers]
        FS_ONLINE[Online Feature Store<br/>Redis Cluster]
        FS_OFFLINE[Offline Feature Store<br/>PostgreSQL + Parquet]
    end

    %% Evaluation Engine
    subgraph EvalEngine["Evaluation Engine"]
        T1[Tier 1: Rule-Based<br/>Grammar, Format, Length]
        T2[Tier 2: ML Model<br/>DeBERTa + XGBoost]
        T3[Tier 3: LLM Judge<br/>GPT-4 / Claude]
        AGG[Score Aggregator<br/>Ensemble Combiner]
    end

    %% Decision & Routing
    subgraph Decision["Decision Router"]
        DR[Decision Engine<br/>Threshold-based]
        PASS[PASS Queue]
        REVIEW[REVIEW Queue]
        REJECT[REJECT Queue]
    end

    %% Human Review
    subgraph HumanReview["Human-in-the-Loop"]
        RQ[Review Queue<br/>Redis Streams]
        UI[Review UI<br/>React + WebSocket]
        REV[Human Reviewers<br/>50-100 annotators]
        ADJ[Adjudication Panel<br/>Senior Reviewers]
    end

    %% Feedback & Training
    subgraph Feedback["Feedback & Training Loop"]
        FC[Feedback Collector<br/>PostgreSQL]
        DS[Dataset Store<br/>DVC + S3]
        TP[Training Pipeline<br/>Airflow + Ray]
        MR[Model Registry<br/>MLflow]
    end

    %% Monitoring & Observability
    subgraph Monitoring["Monitoring & Observability"]
        PROM[Prometheus<br/>Metrics Collection]
        GRAF[Grafana<br/>Dashboards]
        ALERT[PagerDuty<br/>Alerting]
        DRIFT[Drift Detector<br/>Statistical Tests]
        LOG[Centralized Logging<br/>ELK Stack]
    end

    %% Output
    subgraph Output["Output Layer"]
        OUT_API[Results API<br/>Evaluation Scores]
        STORE[Results Store<br/>PostgreSQL]
        ANALYTICS[Analytics<br/>Business Dashboards]
    end

    %% Connections - Generation Flow
    Sources --> QG
    PT --> QG
    GM --> QG
    QG --> API

    %% Connections - Ingestion
    LB --> API
    API --> VAL
    VAL --> KF
    KF -.->|failed| DLQ

    %% Connections - Feature Engineering
    KF --> FE
    FE --> EMB
    FE --> FS_ONLINE
    FE --> FS_OFFLINE

    %% Connections - Evaluation
    FS_ONLINE --> T1
    T1 -->|passes 85%| T2
    T1 -->|rejects 15%| REJECT
    T2 --> AGG
    T2 -.->|uncertain 10%| T3
    T3 --> AGG
    AGG --> DR

    %% Connections - Decision
    DR --> PASS
    DR --> REVIEW
    DR --> REJECT

    %% Connections - Human Review
    REVIEW --> RQ
    RQ --> UI
    UI --> REV
    REV -->|disagreement| ADJ
    REV --> FC
    ADJ --> FC

    %% Connections - Feedback Loop
    FC --> DS
    DS --> TP
    TP --> MR
    MR -->|deploy| T2
    MR -->|update prompts| T3

    %% Connections - Monitoring
    T1 --> PROM
    T2 --> PROM
    T3 --> PROM
    DR --> PROM
    PROM --> GRAF
    PROM --> ALERT
    PROM --> DRIFT
    DRIFT -->|trigger| TP
    API --> LOG
    FE --> LOG

    %% Connections - Output
    PASS --> STORE
    REJECT --> STORE
    FC --> STORE
    STORE --> OUT_API
    STORE --> ANALYTICS

    %% Styling
    classDef source fill:#e1f5fe,stroke:#01579b
    classDef gen fill:#f3e5f5,stroke:#4a148c
    classDef ingest fill:#e8f5e9,stroke:#1b5e20
    classDef queue fill:#fff3e0,stroke:#e65100
    classDef feature fill:#fce4ec,stroke:#880e4f
    classDef eval fill:#e8eaf6,stroke:#1a237e
    classDef decision fill:#f1f8e9,stroke:#33691e
    classDef human fill:#fff8e1,stroke:#f57f17
    classDef feedback fill:#e0f2f1,stroke:#004d40
    classDef monitor fill:#fbe9e7,stroke:#bf360c
    classDef output fill:#f5f5f5,stroke:#212121

    class SD,MN,KB source
    class QG,PT,GM gen
    class API,LB,VAL ingest
    class KF,DLQ queue
    class FE,EMB,FS_ONLINE,FS_OFFLINE feature
    class T1,T2,T3,AGG eval
    class DR,PASS,REVIEW,REJECT decision
    class RQ,UI,REV,ADJ human
    class FC,DS,TP,MR feedback
    class PROM,GRAF,ALERT,DRIFT,LOG monitor
    class OUT_API,STORE,ANALYTICS output
```

## Component Details

### Service Inventory

| Service | Technology | Scaling | SLA |
|---------|-----------|---------|-----|
| Load Balancer | NGINX / AWS ALB | Managed | 99.99% |
| API Service | FastAPI (Python 3.11) | HPA: 2-20 pods | 99.9% |
| Kafka Cluster | Apache Kafka 3.x | 32 partitions, RF=3 | 99.95% |
| Feature Extractor | Ray Workers (Python) | Auto-scale on queue depth | 99.9% |
| Embedding Service | sentence-transformers | GPU pods, batch inference | 99.9% |
| Redis Cluster | Redis 7.x | 6 nodes + replicas | 99.9% |
| Tier 1 Engine | Python rule engine | Co-located with API | 99.9% |
| Tier 2 Engine | DeBERTa + XGBoost | GPU pods (A100) | 99.9% |
| Tier 3 Engine | OpenAI/Anthropic API | Rate-limited, circuit breaker | 99.5% |
| Decision Router | Python service | Stateless, HPA | 99.9% |
| Review UI | React + Next.js | CDN + 3 pods | 99.9% |
| Feedback DB | PostgreSQL 15 | Primary + 2 read replicas | 99.9% |
| Training Pipeline | Airflow + Ray | On-demand GPU | Best effort |
| MLflow | MLflow 2.x | Single instance + S3 | 99.5% |
| Prometheus | Prometheus + Thanos | HA pair | 99.9% |
| Grafana | Grafana 10.x | 2 pods | 99.5% |

### Network Architecture

```mermaid
graph LR
    subgraph PublicZone["Public Zone"]
        LB[Load Balancer]
        CDN[CDN / Static Assets]
    end

    subgraph AppZone["Application Zone"]
        API[API Pods]
        UI[Review UI]
    end

    subgraph DataZone["Data Zone"]
        KF[Kafka]
        REDIS[Redis]
        PG[PostgreSQL]
    end

    subgraph ComputeZone["GPU Compute Zone"]
        EVAL[Evaluation Pods]
        TRAIN[Training Pods]
    end

    subgraph ExternalZone["External APIs"]
        OAI[OpenAI API]
        ANT[Anthropic API]
    end

    LB --> API
    CDN --> UI
    API --> KF
    API --> REDIS
    KF --> EVAL
    EVAL --> REDIS
    EVAL --> PG
    EVAL --> OAI
    EVAL --> ANT
    TRAIN --> PG
    UI --> API
```

### Data Flow Summary

1. **Ingestion:** Documents → Question Generator → API → Kafka
2. **Feature Computation:** Kafka → Feature Extractor → Redis (online) + PostgreSQL (offline)
3. **Evaluation:** Features → Tier 1 → Tier 2 → (optional) Tier 3 → Score Aggregation
4. **Routing:** Scores → Decision Router → Pass / Review / Reject queues
5. **Human Review:** Review queue → UI → Reviewer → Feedback Collector
6. **Feedback Loop:** Feedback → Dataset Store → Training Pipeline → Model Registry → Deploy
7. **Monitoring:** All services → Prometheus → Grafana + Alerts → Drift Detection → Retrain trigger
