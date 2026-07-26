"""Feature extraction pipeline.

Computes text, semantic, reference, safety, and duplicate features
for each question. Supports both real-time and batch computation.
"""

from __future__ import annotations

import logging
import re

from src.utils.models import EvaluationInput, FeatureVector

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extracts features from question-document pairs.

    Feature categories:
    - Text: length, readability, grammar, structure
    - Semantic: embedding similarity, topic alignment
    - Reference: BLEU, ROUGE, BERTScore
    - Safety: toxicity, bias, PII
    - Duplicate: MinHash, semantic dedup
    """

    def __init__(self):
        # In production: load models
        # self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # self.nlp = spacy.load('en_core_web_sm')
        pass

    async def extract(self, input: EvaluationInput) -> FeatureVector:
        """Extract all features for a question-document pair."""
        text_features = self._compute_text_features(input)
        semantic_features = await self._compute_semantic_features(input)
        reference_features = self._compute_reference_features(input)
        safety_features = self._compute_safety_features(input)
        duplicate_features = self._compute_duplicate_features(input)

        return FeatureVector(
            evaluation_id=input.evaluation_id or "unknown",
            text_features=text_features,
            semantic_features=semantic_features,
            reference_features=reference_features,
            safety_features=safety_features,
            duplicate_features=duplicate_features,
        )

    def _compute_text_features(self, input: EvaluationInput) -> dict[str, float]:
        """Compute surface-level text features (< 5ms)."""
        question = input.generated_question
        answer = input.expected_answer

        words = question.split()
        sentences = re.split(r'[.!?]+', question)

        features = {
            "question_char_length": float(len(question)),
            "question_word_count": float(len(words)),
            "answer_char_length": float(len(answer)),
            "answer_word_count": float(len(answer.split())),
            "sentence_count": float(len([s for s in sentences if s.strip()])),
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "has_question_mark": float(question.strip().endswith("?")),
            "starts_with_capital": float(question[0].isupper() if question else 0),
            "question_type_who": float(bool(re.match(r'(?i)^who\b', question))),
            "question_type_what": float(bool(re.match(r'(?i)^what\b', question))),
            "question_type_why": float(bool(re.match(r'(?i)^why\b', question))),
            "question_type_how": float(bool(re.match(r'(?i)^how\b', question))),
            "question_type_when": float(bool(re.match(r'(?i)^when\b', question))),
            "question_type_where": float(bool(re.match(r'(?i)^where\b', question))),
        }

        # Readability approximation (Flesch-Kincaid simplified)
        syllable_count = sum(self._count_syllables(w) for w in words)
        if len(words) > 0 and len(sentences) > 0:
            fk_grade = (
                0.39 * (len(words) / len(sentences))
                + 11.8 * (syllable_count / len(words))
                - 15.59
            )
            features["readability_grade"] = max(0.0, min(20.0, fk_grade))
        else:
            features["readability_grade"] = 0.0

        return features

    async def _compute_semantic_features(self, input: EvaluationInput) -> dict[str, float]:
        """Compute semantic similarity features (< 50ms)."""
        # In production:
        # q_embedding = self.embedding_model.encode(input.generated_question)
        # s_embedding = self.embedding_model.encode(input.source_document[:512])
        # similarity = cosine_similarity(q_embedding, s_embedding)

        # Placeholder values
        return {
            "source_similarity": 0.75,
            "answer_consistency": 0.80,
            "embedding_distance": 0.25,
            "topic_alignment": 0.82,
            "entity_overlap_ratio": 0.60,
        }

    def _compute_reference_features(self, input: EvaluationInput) -> dict[str, float]:
        """Compute reference-based metrics (< 100ms)."""
        # In production:
        # bleu = sacrebleu.sentence_bleu(input.expected_answer, [reference])
        # rouge = rouge_scorer.score(input.source_document, input.generated_question)

        # Simplified n-gram overlap
        q_words = set(input.generated_question.lower().split())
        s_words = set(input.source_document.lower().split()[:200])
        a_words = set(input.expected_answer.lower().split())

        q_s_overlap = len(q_words & s_words) / max(len(q_words), 1)
        q_a_overlap = len(q_words & a_words) / max(len(q_words), 1)

        return {
            "bleu_score": 0.0,  # Placeholder — needs reference translation
            "rouge_1": q_s_overlap,
            "rouge_l": q_s_overlap * 0.8,  # Approximation
            "bertscore_f1": 0.0,  # Placeholder — needs model
            "question_source_overlap": q_s_overlap,
            "question_answer_overlap": q_a_overlap,
        }

    def _compute_safety_features(self, input: EvaluationInput) -> dict[str, float]:
        """Compute safety and bias features (< 50ms)."""
        # In production:
        # toxicity = detoxify.predict(input.generated_question)
        # bias = bias_classifier.predict(input.generated_question)
        # pii = presidio_analyzer.analyze(input.generated_question)

        return {
            "toxicity_score": 0.01,  # Placeholder
            "bias_score": 0.02,
            "pii_detected": 0.0,
            "sentiment_polarity": 0.0,
        }

    def _compute_duplicate_features(self, input: EvaluationInput) -> dict[str, float]:
        """Compute duplicate detection features (< 20ms)."""
        # In production:
        # minhash = MinHash(num_perm=128)
        # for word in input.generated_question.split():
        #     minhash.update(word.encode('utf-8'))
        # Check against existing questions in FAISS index

        return {
            "minhash_similarity": 0.0,  # Placeholder
            "semantic_dedup_score": 0.0,
            "exact_match_ratio": 0.0,
        }

    @staticmethod
    def _count_syllables(word: str) -> int:
        """Approximate syllable count for English words."""
        word = word.lower().strip(".,!?;:")
        if len(word) <= 3:
            return 1
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e"):
            count -= 1
        return max(count, 1)
