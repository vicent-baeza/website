from collections.abc import MutableMapping
from typing import Iterator, TypeVar

K = TypeVar("K")
V = TypeVar("V")


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
