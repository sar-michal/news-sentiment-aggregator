import logging
import os
from typing import Any, Dict, List

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
        pipe_outputs = self.sentiment_pipe(raw_sentence_texts, top_k=None)

        processed_sentences = []
        running_total_sentiment = 0.0

        for idx, (sent_text, output_list) in enumerate(zip(raw_sentence_texts, pipe_outputs)):
            pos_score = 0.0
            neg_score = 0.0
            
            for pred in output_list:
                label = pred["label"].lower().strip()
                weight = self.label_weights.get(label, 0.0)
                if weight == 1.0:
                    pos_score += pred["score"]
                elif weight == -1.0:
                    neg_score += pred["score"]
            
            continuous_score = pos_score - neg_score
            running_total_sentiment += continuous_score

            processed_sentences.append(
                {
                    "sequence_index": idx,
                    "text": sent_text,
                    "sentiment_score": round(continuous_score, 4),
                }
            )

        overall_sentiment = round(running_total_sentiment / len(raw_sentences), 4)

        # ==========================================
        # PASS 2: ABSA
        # ==========================================

        target_labels = {"ORG", "PERSON", "GPE", "PRODUCT", "NORP", "EVENT"}
        
        # For deduplication
        unique_inference_pairs = set()

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
                    unique_inference_pairs.add((clean_matched_text, ent_name, ent.label_))

        unique_inference_pairs = list(unique_inference_pairs)
        entity_tracker: Dict[tuple, List[float]] = {}

        batch_size = 16

        for i in range(0, len(unique_inference_pairs), batch_size):
            batch = unique_inference_pairs[i : i + batch_size]
            
            batch_sentences = [pair[0] for pair in batch]
            batch_entities = [pair[1] for pair in batch]

            inputs = self.absa_tokenizer(
                batch_sentences,
                batch_entities,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            ).to(self.device)

            with torch.no_grad():
                outputs = self.absa_model(**inputs)
                
                # Softmax to convert into probability percentages
                probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()

            for pair, prob in zip(batch, probs):
                ent_name = pair[1]
                ent_type = pair[2]
                
                # 0: Negative, 1: Neutral, 2: Positive
                p_neg = float(prob[0])
                p_pos = float(prob[2])
                
                absa_score = p_pos - p_neg

                key = (ent_name, ent_type)
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