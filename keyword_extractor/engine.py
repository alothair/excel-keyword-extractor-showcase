"""Pure keyword-scoring logic."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math
import re
from typing import Iterable

TOKEN = re.compile(r"[\w]+(?:[-'][\w]+)?", re.UNICODE)
DEFAULT_STOP_WORDS = frozenset(
    "a an and are as at be by for from has in is it its of on or that the to was were with".split()
)


@dataclass(frozen=True, slots=True)
class Keyword:
    keyword: str
    score: float
    occurrences: int
    document_frequency: int

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


def _terms(text: str, stop_words: frozenset[str], include_phrases: bool) -> list[str]:
    tokens = [
        value.casefold()
        for value in TOKEN.findall(text)
        if len(value) > 1 and value.casefold() not in stop_words and not value.isdigit()
    ]
    if not include_phrases:
        return tokens
    return tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]


def extract_keywords(
    documents: Iterable[str],
    *,
    top: int = 20,
    stop_words: Iterable[str] = (),
    include_phrases: bool = True,
) -> list[Keyword]:
    """Rank terms across documents using normalized TF-IDF."""
    if top < 1:
        raise ValueError("top must be at least 1")
    excluded = DEFAULT_STOP_WORDS | frozenset(word.casefold() for word in stop_words)
    counters = [Counter(_terms(text, excluded, include_phrases)) for text in documents if text.strip()]
    counters = [counter for counter in counters if counter]
    if not counters:
        return []
    document_frequency: Counter[str] = Counter()
    occurrences: Counter[str] = Counter()
    score: Counter[str] = Counter()
    for counter in counters:
        document_frequency.update(counter.keys())
        occurrences.update(counter)
        total = sum(counter.values())
        for term, count in counter.items():
            score[term] += count / total
    count_documents = len(counters)
    ranked = []
    for term, tf in score.items():
        idf = math.log((1 + count_documents) / (1 + document_frequency[term])) + 1
        phrase_boost = 1.2 if " " in term else 1.0
        ranked.append(Keyword(term, round((tf / count_documents) * idf * phrase_boost, 6), occurrences[term], document_frequency[term]))
    ranked.sort(key=lambda item: (-item.score, -item.occurrences, item.keyword))
    return ranked[:top]
