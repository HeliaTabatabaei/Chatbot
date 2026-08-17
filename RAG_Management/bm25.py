# bm25.py
from typing import List, Dict
import re
from collections import Counter
import math
import pickle


class PersianBM25Encoder:
    """BM25 encoder for Persian texts"""

    def __init__(self):
        self.idf_scores = {}
        self.vocab = {}
        self.k1 = 1.5
        self.b = 0.75
        self.avgdl = 0  # average length of document

    def tokenize(self, text: str) -> List[str]:
        """simple persian bm25 tokenizer"""
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = [t.strip() for t in text.split() if t.strip()]
        return tokens

    def build_vocab_from_texts(self, texts: List[str]):
        """build vocabulary and IDF from list of texts"""
        all_tokens = Counter()
        doc_count = len(texts)
        total_length = 0

        for text in texts:
            tokens = self.tokenize(text)
            total_length += len(tokens)
            all_tokens.update(set(tokens))  # unique tokens per doc

        self.avgdl = total_length / doc_count if doc_count > 0 else 0

        # build vocab
        self.vocab = {token: idx for idx, token in enumerate(all_tokens.keys())}

        # calculate IDF
        for token, doc_freq in all_tokens.items():
            idf = math.log((doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            self.idf_scores[token] = idf

    def encode_document(self, text: str) -> Dict[int, float]:
        """convert  document to sparse vector (for ingest)"""
        tokens = self.tokenize(text)
        token_counts = Counter(tokens)
        doc_length = len(tokens)

        sparse_vector = {}
        for token, count in token_counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                idf = self.idf_scores.get(token, 1.0)

                # BM25 formula
                tf = count / doc_length if doc_length > 0 else 0
                norm = 1 - self.b + self.b * (doc_length / self.avgdl) if self.avgdl > 0 else 1
                score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)

                sparse_vector[idx] = score

        return sparse_vector

    def encode_query(self, query: str) -> Dict[int, float]:
        """convert query to sparse vector (for search)"""
        tokens = self.tokenize(query)
        token_counts = Counter(tokens)

        sparse_vector = {}
        for token, count in token_counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                idf = self.idf_scores.get(token, 1.0)
                score = idf * (count * (self.k1 + 1)) / (count + self.k1)
                sparse_vector[idx] = score

        return sparse_vector

    def save(self, path: str):
        """save vocab and idf"""
        data = {
            "vocab": self.vocab,
            "idf_scores": self.idf_scores,
            "avgdl": self.avgdl,
            "k1": self.k1,
            "b": self.b
        }

        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str):
        """loading vocab and idf"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.vocab = data["vocab"]
        self.idf_scores = data["idf_scores"]
        self.avgdl = data["avgdl"]
        self.k1 = data["k1"]
        self.b = data["b"]
