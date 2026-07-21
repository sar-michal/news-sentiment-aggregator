from unittest.mock import MagicMock

import app.services.nlp as nlp_module
import pytest
import torch
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


class DummyDocComplex:
    def __init__(self):
        self.sents = [
            DummySpan("The UN announced a treaty.", 0, 26),
            DummySpan("Apple Inc's stock fell.", 27, 50),
            DummySpan("Apple also released a phone.", 51, 79),
            DummySpan("god was thanked.", 80, 96),
            DummySpan("the alps are cold.", 97, 115),
        ]
        self.ents = [
            DummySpan("The UN", 0, 6, "ORG"),  # Should strip "The "
            DummySpan("Apple Inc's", 27, 38, "ORG"),  # Should strip "'s"
            DummySpan("Apple", 51, 56, "ORG"),  # Should merge into "Apple Inc"
            DummySpan("god", 80, 83, "PERSON"),  # Lowercase PERSON: Should drop
            DummySpan(
                "the alps", 97, 105, "GPE"
            ),  # Should strip "the ", title case -> "Alps"
        ]


@pytest.fixture
def nlp_processor(monkeypatch):
    """
    Fixture that initializes the NLPProcessor and mocks spaCy
    and Hugging Face model classes.
    """
    mock_spacy_load = MagicMock()
    monkeypatch.setattr(nlp_module.spacy, "load", mock_spacy_load)

    mock_pipeline = MagicMock()
    monkeypatch.setattr(nlp_module, "pipeline", mock_pipeline)

    mock_tokenizer_class = MagicMock()
    monkeypatch.setattr(nlp_module, "AutoTokenizer", mock_tokenizer_class)

    mock_model_class = MagicMock()
    monkeypatch.setattr(
        nlp_module, "AutoModelForSequenceClassification", mock_model_class
    )

    monkeypatch.setattr(nlp_module.torch, "device", MagicMock())

    processor = NLPProcessor()

    return processor


@pytest.mark.parametrize("invalid_text", ["", "   ", None])
def test_process_article_returns_empty_schema_for_blank_text(
    nlp_processor, invalid_text
):
    payload = nlp_processor.process_article(invalid_text)

    assert payload["sentiment_score"] == 0.0
    assert len(payload["sentences"]) == 0
    assert len(payload["entities"]) == 0


def test_process_article_maps_entities_to_sentence_sentiment_successfully(
    nlp_processor, monkeypatch
):
    nlp_processor.nlp.return_value = DummyDoc()

    nlp_processor.sentiment_pipe.return_value = [
        [
            {"label": "positive", "score": 0.8},
            {"label": "neutral", "score": 0.1},
            {"label": "negative", "score": 0.1},
        ],
        [
            {"label": "negative", "score": 0.6},
            {"label": "neutral", "score": 0.3},
            {"label": "positive", "score": 0.1},
        ],
    ]

    nlp_processor.absa_tokenizer.return_value.to.return_value = {"input_ids": "mock"}

    class MockOutput:
        def __init__(self):
            self.logits = "mock_logits"

    nlp_processor.absa_model.return_value = MockOutput()

    def mock_softmax(logits, dim):
        return torch.tensor(
            [
                [0.1, 0.1, 0.8],
                [0.1, 0.1, 0.8],
            ]
        )

    monkeypatch.setattr(nlp_module.torch, "softmax", mock_softmax)

    payload = nlp_processor.process_article("Fake article text.")

    assert payload["sentiment_score"] == 0.10

    assert len(payload["sentences"]) == 2
    assert payload["sentences"][0]["sentiment_score"] == 0.70
    assert payload["sentences"][1]["sentiment_score"] == -0.50

    assert len(payload["entities"]) == 2

    un_entity = next(e for e in payload["entities"] if e["entity"] == "UN")
    assert un_entity["type"] == "ORG"
    assert un_entity["sentiment"] == 0.70

    apple_entity = next(e for e in payload["entities"] if e["entity"] == "Apple")
    assert apple_entity["type"] == "ORG"
    assert apple_entity["sentiment"] == 0.70


def test_process_article_data_cleaning_and_coreference(nlp_processor, monkeypatch):
    nlp_processor.nlp.return_value = DummyDocComplex()

    nlp_processor.sentiment_pipe.return_value = [
        [
            {"label": "positive", "score": 0.8},
            {"label": "neutral", "score": 0.1},
            {"label": "negative", "score": 0.1},
        ]
        for _ in range(5)
    ]

    nlp_processor.absa_tokenizer.return_value.to.return_value = {"input_ids": "mock"}

    class MockOutput:
        def __init__(self):
            self.logits = "mock_logits"

    nlp_processor.absa_model.return_value = MockOutput()

    def mock_softmax(logits, dim):
        # 'god' is dropped, leaving 4 valid pairs
        return torch.tensor(
            [
                [0.1, 0.1, 0.8],  # The UN -> UN
                [0.1, 0.1, 0.8],  # Apple Inc's -> Apple Inc
                [0.1, 0.1, 0.8],  # Apple -> Apple (Aggregated later)
                [0.1, 0.1, 0.8],  # the alps -> alps (Titlecased later)
            ]
        )

    monkeypatch.setattr(nlp_module.torch, "softmax", mock_softmax)

    payload = nlp_processor.process_article("Fake dirty article.")

    # "Apple" and "Apple Inc" merge into 1
    assert len(payload["entities"]) == 3

    entity_names = [e["entity"] for e in payload["entities"]]

    assert "UN" in entity_names
    assert "Apple Inc" in entity_names
    assert "Alps" in entity_names

    assert "god" not in entity_names
    assert "Apple" not in entity_names
    assert "alps" not in entity_names


def test_process_article_handles_text_with_zero_extractable_entities(nlp_processor):
    nlp_processor.nlp.return_value = DummyDocNoEntities()

    nlp_processor.sentiment_pipe.return_value = [
        [
            {"label": "positive", "score": 0.85},
            {"label": "neutral", "score": 0.10},
            {"label": "negative", "score": 0.05},
        ]
    ]

    payload = nlp_processor.process_article("Sunny day data.")

    assert payload["sentiment_score"] == 0.80
    assert len(payload["sentences"]) == 1
    assert payload["sentences"][0]["text"] == "The weather is pleasant today."
    assert payload["sentences"][0]["sentiment_score"] == 0.80
    assert len(payload["entities"]) == 0

    nlp_processor.absa_model.assert_not_called()
