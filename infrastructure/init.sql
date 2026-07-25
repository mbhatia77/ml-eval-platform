-- Database initialization for the ML Evaluation Platform

-- Evaluation results
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id UUID PRIMARY KEY,
    quality_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('pass', 'review', 'reject')),
    tier_used SMALLINT NOT NULL,
    latency_ms FLOAT NOT NULL,
    explanation TEXT,
    human_review_recommended BOOLEAN DEFAULT FALSE,
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dimension scores (one row per dimension per evaluation)
CREATE TABLE IF NOT EXISTS dimension_scores (
    id SERIAL PRIMARY KEY,
    evaluation_id UUID NOT NULL REFERENCES evaluations(evaluation_id),
    dimension VARCHAR(30) NOT NULL,
    score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    explanation TEXT
);

-- Evaluation inputs (stored for retraining)
CREATE TABLE IF NOT EXISTS evaluation_inputs (
    evaluation_id UUID PRIMARY KEY REFERENCES evaluations(evaluation_id),
    source_document TEXT NOT NULL,
    generated_question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    document_type VARCHAR(30),
    domain VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    generation_model VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Human reviews
CREATE TABLE IF NOT EXISTS human_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(evaluation_id),
    reviewer_id VARCHAR(100) NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('pass', 'review', 'reject')),
    feedback TEXT,
    time_spent_seconds FLOAT,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Review dimension scores
CREATE TABLE IF NOT EXISTS review_dimension_scores (
    id SERIAL PRIMARY KEY,
    review_id UUID NOT NULL REFERENCES human_reviews(review_id),
    dimension VARCHAR(30) NOT NULL,
    score FLOAT NOT NULL
);

-- Reviewer metrics
CREATE TABLE IF NOT EXISTS reviewers (
    reviewer_id VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(200),
    domains TEXT[], -- Array of expert domains
    reliability_score FLOAT DEFAULT 0.8,
    total_reviews INTEGER DEFAULT 0,
    agreement_rate FLOAT DEFAULT 0.0,
    avg_review_time_seconds FLOAT,
    active BOOLEAN DEFAULT TRUE
);

-- Batch evaluations
CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id UUID PRIMARY KEY,
    input_path TEXT NOT NULL,
    output_path TEXT,
    status VARCHAR(20) DEFAULT 'accepted',
    total_questions INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    reviewed INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Model registry (supplements MLflow)
CREATE TABLE IF NOT EXISTS model_versions (
    version VARCHAR(50) PRIMARY KEY,
    model_type VARCHAR(50) NOT NULL,
    data_version VARCHAR(100),
    f1_score FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    auc_roc FLOAT,
    status VARCHAR(20) DEFAULT 'staging',
    deployed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_evaluations_decision ON evaluations(decision);
CREATE INDEX idx_evaluations_created ON evaluations(created_at);
CREATE INDEX idx_evaluations_domain ON evaluation_inputs(domain);
CREATE INDEX idx_reviews_evaluation ON human_reviews(evaluation_id);
CREATE INDEX idx_reviews_reviewer ON human_reviews(reviewer_id);
CREATE INDEX idx_batch_status ON batch_jobs(status);
