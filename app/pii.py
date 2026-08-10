from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.session_store import SessionStore


@dataclass(frozen=True)
class ProtectionResult:
    protected_text: str
    detected_entities: dict[str, int]


class PiiProtector:
    def __init__(self, analyzer: AnalyzerEngine) -> None:
        self.analyzer = analyzer

    def protect(self, session_id: str, text: str, store: SessionStore) -> ProtectionResult:
        results = self.analyzer.analyze(text=text, language="en")
        # Prefer longer spans and higher confidence when recognizers overlap.
        selected = self._non_overlapping(results)
        counts = Counter(result.entity_type for result in selected)
        protected = text
        for result in sorted(selected, key=lambda item: item.start, reverse=True):
            token = store.protect_value(session_id, result.entity_type, text[result.start : result.end])
            protected = protected[: result.start] + token + protected[result.end :]
        return ProtectionResult(protected_text=protected, detected_entities=dict(counts))

    @staticmethod
    def _non_overlapping(results):
        selected = []
        occupied: list[tuple[int, int]] = []
        for result in sorted(results, key=lambda item: (-(item.end - item.start), -item.score)):
            if all(result.end <= start or result.start >= end for start, end in occupied):
                selected.append(result)
                occupied.append((result.start, result.end))
        return selected


@lru_cache
def build_protector() -> PiiProtector:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
    return PiiProtector(AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"]))
