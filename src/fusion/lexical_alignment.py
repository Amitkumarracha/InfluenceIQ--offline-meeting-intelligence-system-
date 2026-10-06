"""Sparse TF-IDF slide matching. Lexical relevance, not semantic entailment."""
import math
from collections import Counter
from src.utils.text import words


class TfidfIndex:
    def __init__(self, texts):
        counts = [Counter(words(text)) for text in texts]
        frequency = Counter(term for count in counts for term in count)
        self.idf = {term: 1 + math.log((1 + len(counts)) / (1 + n))
                    for term, n in frequency.items()}
        self.postings = {}
        for index, count in enumerate(counts):
            for term, weight in self.vector(count).items():
                self.postings.setdefault(term, []).append((index, weight))
        self.size = len(counts)

    def vector(self, count):
        weights = {term: (1 + math.log(n)) * self.idf[term]
                   for term, n in count.items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in weights.values()))
        return {term: value / norm for term, value in weights.items()} if norm else {}

    def scores(self, text):
        scores = [0.0] * self.size
        for term, weight in self.vector(Counter(words(text))).items():
            for index, value in self.postings.get(term, []):
                scores[index] += weight * value
        return [min(1.0, max(0.0, value)) for value in scores]
