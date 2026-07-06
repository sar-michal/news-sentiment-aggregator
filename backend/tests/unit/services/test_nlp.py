from unittest.mock import MagicMock

import app.services.nlp as nlp_module
import pytest
from app.services.nlp import NLPProcessor


class DummySpan:
    def __init__(self, text: str, start_char: int, end_char: int, label_: str = None):
        self.text = text
        self.start_char = start_char
        self.end_char = end_char
        self.label_ = label_


class DummyDoc:
    def __init__(self):
        self.sents = [
            DummySpan("The UN announced a treaty.", 0, 26),
            DummySpan("However, Apple stock fell.", 27, 53),
        ]
        self.ents = [
            DummySpan("UN", 4, 6, "ORG"),
            DummySpan("Apple", 36, 41, "ORG"),
        ]


class DummyDocNoEntities:
    def __init__(self):
        self.sents = [DummySpan("The weather is pleasant today.", 0, 30)]
        self.ents = []


@pytest.fixture
def nlp_processor(monkeypatch):
    """
    Fixture that initializes the NLPProcessor and mocks spaCy
    and Hugging Face model loading.
    """
    mock_spacy_load = MagicMock()
    monkeypatch.setattr(nlp_module.spacy, "load", mock_spacy_load)

    mock_pipeline = MagicMock()
    monkeypatch.setattr(nlp_module, "pipeline", mock_pipeline)

    processor = NLPProcessor()

    return processor


@pytest.mark.parametrize(
    "incoming_label, score, expected_output",
    [
        # Standard labels
        ("positive", 0.9, 0.9),
        ("negative", 0.8, -0.8),
        ("neutral", 0.99, 0.0),
        ("unknown_label", 0.5, 0.0),
        # Alternative labels
        ("label_0", 0.9, -0.9),
        ("label_1", 0.5, 0.0),
        ("label_2", 0.8, 0.8),
        ("neg", 0.75, -0.75),
        ("neu", 0.11, 0.0),
        ("pos", 0.65, 0.65),
    ],
)
def test_convert_score_handles_all_label_variations(
    nlp_processor, incoming_label, score, expected_output
):
    actual = nlp_processor._convert_score(incoming_label, score)
    assert actual == expected_output


@pytest.mark.parametrize("invalid_text", ["", "   ", None])
def test_process_article_returns_empty_schema_for_blank_text(
    nlp_processor, invalid_text
):
    """Verifies the early-exit guardrails for empty or null text payloads."""
    payload = nlp_processor.process_article(invalid_text)

    assert payload["sentiment_score"] == 0.0
    assert len(payload["sentences"]) == 0
    assert len(payload["entities"]) == 0


def test_process_article_maps_entities_to_sentence_sentiment_successfully(
    nlp_processor,
):
    nlp_processor.nlp.return_value = DummyDoc()

    nlp_processor.sentiment_pipe.return_value = [
        {"label": "positive", "score": 0.8},
        {"label": "negative", "score": 0.6},
    ]

    payload = nlp_processor.process_article("Fake article text.")

    # Overall sentiment (average of 0.8 and -0.6 = 0.1)
    assert payload["sentiment_score"] == 0.1

    assert len(payload["sentences"]) == 2
    assert payload["sentences"][0]["sentiment_score"] == 0.8
    assert payload["sentences"][1]["sentiment_score"] == -0.6

    assert len(payload["entities"]) == 2

    un_entity = next(e for e in payload["entities"] if e["entity"] == "UN")
    assert un_entity["type"] == "ORG"
    assert un_entity["sentiment"] == 0.8

    apple_entity = next(e for e in payload["entities"] if e["entity"] == "Apple")
    assert apple_entity["type"] == "ORG"
    assert apple_entity["sentiment"] == -0.6


def test_process_article_handles_text_with_zero_extractable_entities(nlp_processor):
    nlp_processor.nlp.return_value = DummyDocNoEntities()
    nlp_processor.sentiment_pipe.return_value = [{"label": "positive", "score": 0.95}]

    payload = nlp_processor.process_article("Sunny day data.")

    assert payload["sentiment_score"] == 0.95
    assert len(payload["sentences"]) == 1
    assert payload["sentences"][0]["text"] == "The weather is pleasant today."
    assert len(payload["entities"]) == 0
