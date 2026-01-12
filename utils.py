from collections.abc import MutableMapping
from typing import Iterator, TypeVar, Any, Iterable
from math import log
from dataclasses import dataclass

K = TypeVar("K")
V = TypeVar("V")

WORD_TRIE_CONST = 2**16

@dataclass
class SearchSite:
    title: str
    path: str
    priority: int

class ListDict(MutableMapping[K, list[V]]):
    def __init__(self) -> None:
        self.dict: dict[K, list[V]] = {}
        self.pending_values: list[V] = []

    def __setitem__(self, key: K, value: list[V]) -> None:
        return self.dict.__setitem__(key, value)

    def __getitem__(self, key: K) -> list[V]:
        return self.dict.__getitem__(key)

    def __delitem__(self, key: K) -> None:
        self.dict.__delitem__(key)

    def __iter__(self) -> Iterator[K]:
        return self.dict.__iter__()

    def __len__(self) -> int:
        return self.dict.__len__()

    def append(self, value: V):
        self.pending_values.append(value)

    def add(self, key: K):
        if key in self:
            self[key].extend(self.pending_values)
        else:
            self[key] = self.pending_values
        self.pending_values = []


class WordScoreTrie:
    def __init__(self):
        self.children: dict[str, WordScoreTrie] = {}
        self.leaf_scores: dict[int, int] | None = None
        self.total_scores: dict[int, int] | None = None

    def add(self, word: str, scores: dict[int, int], total_number_of_documents):
        if len(word) == 0:
            if self.leaf_scores is None:
                self.leaf_scores = {}

            adjusted_idf_term = log(total_number_of_documents / (1 + len(scores))) + 1
            for idx, score in scores.items():
                if idx not in self.leaf_scores:
                    self.leaf_scores[idx] = 0
                self.leaf_scores[idx] += int(10000 * score * adjusted_idf_term * WORD_TRIE_CONST) # TF-IDF (more or less, but TF is the score)
            return
        self.total_scores = None
        if word[0] not in self.children:
            self.children[word[0]] = WordScoreTrie()
        self.children[word[0]].add(word[1:], scores, total_number_of_documents)

    @property
    def scores(self) -> dict[int, int]:
        if self.total_scores is None:
            self.total_scores = self.leaf_scores.copy() if self.leaf_scores is not None else {}
            for child in self.children.values():
                for score_idx, score in child.scores.items():
                    if score <= 1:
                        continue
                    if score_idx not in self.total_scores:
                        self.total_scores[score_idx] = 0
                    self.total_scores[score_idx] += int(score * 0.8)
        return self.total_scores

    def as_dict(self, score_confs: list[list[int]], max_results: int = 5) -> dict[str, Any]:
        content = {}

        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        selected_scores = [score[0] for score in sorted_scores[:max_results]]

        for idx, score_conf in enumerate(score_confs):
            if score_conf == selected_scores:
                score_conf_idx = idx
                break
        else:
            score_conf_idx = len(score_confs)
            score_confs.append(selected_scores)

        content["S"] = score_conf_idx

        if len(self.children) > 0:
            children_as_dict = {child_letter: child.as_dict(score_confs, max_results) for child_letter, child in self.children.items()}
            content['C'] = children_as_dict
        return content

    def as_dict_cumulative(self, score_confs: list[list[int]], sites: list[SearchSite], max_results: int = 10) -> dict[str, Any]:
        content = {}
        sorted_scores = sorted(self.scores.items(), key=lambda x: sites[x[0]].title)
        sorted_scores = sorted(sorted_scores, key=lambda x: sites[x[0]].priority)
        sorted_scores = sorted(sorted_scores, key=lambda x: x[1], reverse=True)
        selected_scores = [score[0] for score in sorted_scores[:max_results]]

        for idx, score_conf in enumerate(score_confs):
            if score_conf == selected_scores:
                score_conf_idx = idx #f'{idx}: {sorted_scores}'
                break
        else:
            score_conf_idx = len(score_confs) #f'{len(score_confs)}: {sorted_scores}'
            score_confs.append(selected_scores)

        if len(self.children) > 0:
            children_as_dict = {child_letter: child.as_dict_cumulative(score_confs, sites, max_results) for child_letter, child in self.children.items()}
            for child_letter, child_content in children_as_dict.items():
                for child_content_key, child_content_value in child_content.items():
                    content[child_letter + child_content_key] = child_content_value

        content[""] = score_conf_idx
        return content
