import logging
import os
from typing import Any, Dict, List

import numpy as np
import spacy
import torch
import transformers
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

# Prevent OpenMP runtime collisions on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
transformers.utils.logging.set_verbosity_error()
transformers.utils.logging.disable_progress_bar()

logger = logging.getLogger(__name__)


class NLPProcessor:
    def __init__(
        self,
        narrative_model_name: str = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
        absa_model_path: str = "ml_models/newsmtsc_distilroberta_absa",
    ):
        logger.info("Initializing spaCy en_core_web_md model...")
        self.nlp = spacy.load("en_core_web_md")

        logger.info(f"Initializing Narrative pipeline: {narrative_model_name}...")
        self.sentiment_pipe = pipeline(
            "sentiment-analysis",
            model=narrative_model_name,
            tokenizer=narrative_model_name,
        )
        # Label mapping to normalize outputs to a float (-1.0 to 1.0)
        self.label_weights = {
            "positive": 1.0,
            "neutral": 0.0,
            "negative": -1.0,
            # Fallback labels for other models
            "label_0": -1.0,
            "label_1": 0.0,
            "label_2": 1.0,
            "pos": 1.0,
            "neu": 0.0,
            "neg": -1.0,
        }

        logger.info(f"Initializing True ABSA model from: {absa_model_path}...")
        self.absa_tokenizer = AutoTokenizer.from_pretrained(absa_model_path)
        self.absa_model = AutoModelForSequenceClassification.from_pretrained(
            absa_model_path
        )

        self.device = torch.device("cpu")
        self.absa_model.to(self.device)
        self.absa_model.eval()

        self.absa_score_map = {0: -1.0, 1: 0.0, 2: 1.0}

    def _convert_score(self, label: str, score: float) -> float:
        """Converts narrative model label string and confidence score into a normalized float between -1.0 and 1.0."""
        clean_label = label.lower().strip()
        weight = self.label_weights.get(clean_label, 0.0)
        return float(weight * score)

    def process_article(self, text: str) -> Dict[str, Any]:
        """
        Dual-Pass NLP Pipeline:
        1. Pass 1: Sentence & Article overall sentiment
        2. Pass 2: True Target-Dependent Sentiment
        """
        if not text or not text.strip():
            return {"sentences": [], "entities": [], "sentiment_score": 0.0}

        doc = self.nlp(text)

        raw_sentences = [sent for sent in doc.sents if sent.text.strip()]
        if not raw_sentences:
            return {"sentences": [], "entities": [], "sentiment_score": 0.0}

        # ==========================================
        # PASS 1: Narrative analysis
        # ==========================================

        raw_sentence_texts = [" ".join(sent.text.split()) for sent in raw_sentences]
        pipe_outputs = self.sentiment_pipe(raw_sentence_texts)

        processed_sentences = []
        running_total_sentiment = 0.0

        for idx, (sent_text, output) in enumerate(zip(raw_sentence_texts, pipe_outputs)):
            # Cast to standard float
            score = self._convert_score(output["label"], output["score"])
            running_total_sentiment += score

            processed_sentences.append(
                {
                    "sequence_index": idx,
                    "text": sent_text,
                    "sentiment_score": round(score, 4),
                }
            )

        overall_sentiment = round(running_total_sentiment / len(raw_sentences), 4)

        # ==========================================
        # PASS 2: ABSA
        # ==========================================

        # Supported entities
        target_labels = {"ORG", "PERSON", "GPE", "PRODUCT", "NORP", "EVENT"}
        processed_entities: List[Dict[str, Any]] = []

        entity_tracker: Dict[tuple, List[float]] = {}

        for ent in doc.ents:
            if ent.label_ in target_labels:
                ent_name = ent.text.strip()
                if not ent_name:
                    continue

                matched_sent = next(
                    (
                        sent
                        for sent in raw_sentences
                        if ent.start_char >= sent.start_char
                        and ent.end_char <= sent.end_char
                    ),
                    None,
                )

                if matched_sent:
                    clean_matched_text = " ".join(matched_sent.text.split())
                    # Construct Text-Pair Inference: [CLS] Sentence [SEP] Entity [SEP]
                    inputs = self.absa_tokenizer(
                        clean_matched_text,
                        ent_name,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=128,
                    ).to(self.device)

                    with torch.no_grad():
                        outputs = self.absa_model(**inputs)
                        logits = outputs.logits.numpy()
                        pred_idx = int(np.argmax(logits, axis=-1)[0])

                    absa_score = self.absa_score_map[pred_idx]

                    key = (ent_name, ent.label_)
                    if key not in entity_tracker:
                        entity_tracker[key] = []
                    entity_tracker[key].append(absa_score)

        # Aggregate Entity Scores
        processed_entities = []
        for (name, ent_type), scores in entity_tracker.items():
            avg_sentiment = sum(scores) / len(scores)
            processed_entities.append(
                {"entity": name, "type": ent_type, "sentiment": round(avg_sentiment, 4)}
            )

        return {
            "sentences": processed_sentences,
            "entities": processed_entities,
            "sentiment_score": overall_sentiment,
        }
