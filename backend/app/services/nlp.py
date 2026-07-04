import logging
from typing import Any, Dict, List

import spacy
from transformers import pipeline

logger = logging.getLogger(__name__)


class NLPProcessor:
    def __init__(
        self,
        model_name: str = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
    ):
        logger.info("Initializing spaCy en_core_web_md model...")
        self.nlp = spacy.load("en_core_web_md")

        logger.info(
            f"Initializing Hugging Face sentiment pipeline with model: {model_name}..."
        )
        self.sentiment_pipe = pipeline(
            "sentiment-analysis", model=model_name, tokenizer=model_name
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

    def _convert_score(self, label: str, score: float) -> float:
        """Converts model label string and confidence score into a normalized float between -1.0 and 1.0."""
        clean_label = label.lower().strip()
        weight = self.label_weights.get(clean_label, 0.0)
        return float(weight * score)

    def process_article(self, text: str) -> Dict[str, Any]:
        """
        Processes a raw article string through the full NLP pipeline.

        1. Sentence Segmentation (spaCy)
        2. Named Entity Recognition (spaCy)
        3. Batch Sentiment Analysis (Hugging Face DistilRoBERTa)
        4. ABSA Proxy Correlation Mapping
        """
        if not text or not text.strip():
            return {"sentences": [], "entities": [], "sentiment_score": 0.0}

        # Sentencizer & NER
        doc = self.nlp(text)

        raw_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if not raw_sentences:
            return {"sentences": [], "entities": [], "sentiment_score": 0.0}

        # Sentiment Inference
        pipe_outputs = self.sentiment_pipe(raw_sentences)

        processed_sentences = []
        running_total_sentiment = 0.0

        for idx, (sent_text, output) in enumerate(zip(raw_sentences, pipe_outputs)):
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

        # ABSA Proxy Mapping
        # Supported entities
        target_labels = {"ORG", "PERSON", "GPE", "PRODUCT", "NORP", "EVENT"}
        processed_entities: List[Dict[str, Any]] = []

        entity_tracker: Dict[tuple, List[float]] = {}

        for ent in doc.ents:
            if ent.label_ in target_labels:
                ent_name = ent.text.strip()
                if not ent_name:
                    continue

                # Find sentence index for entity
                matched_sent_idx = None
                for idx, sent in enumerate(doc.sents):
                    if (
                        ent.start_char >= sent.start_char
                        and ent.end_char <= sent.end_char
                    ):
                        matched_sent_idx = idx
                        break

                # If found, extract the sentiment score
                if matched_sent_idx is not None and matched_sent_idx < len(
                    processed_sentences
                ):
                    sent_sentiment = processed_sentences[matched_sent_idx][
                        "sentiment_score"
                    ]

                    key = (ent_name, ent.label_)
                    if key not in entity_tracker:
                        entity_tracker[key] = []
                    entity_tracker[key].append(sent_sentiment)

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
