"""Vose Alias Sampler."""

from __future__ import annotations

from decimal import Decimal
import random
import attrs


@attrs.define
class AliasTable:
    probs: list[float]
    alias: list[int]

    @classmethod
    def make(cls, xs: list[float]) -> AliasTable:
        n = len(xs)

        xs_sum = sum(xs)
        xs = [x / xs_sum for x in xs]

        probs: list[Decimal] = [Decimal(0)] * n  # probability table
        alias: list[int] = [0] * n  # alias table
        small: list[int] = []  # stack for p < 1
        large: list[int] = []  # stack for p >= 1

        for i, x in enumerate(xs):
            probs[i] = Decimal(x) * n
            if probs[i] < 1:
                small.append(i)
            else:
                large.append(i)

        while small and large:
            small.sort(key=lambda i: probs[i], reverse=True)
            large.sort(key=lambda i: probs[i], reverse=False)

            s = small.pop()
            l = large.pop()

            alias[s] = l
            probs[l] = (probs[l] + probs[s]) - Decimal(1)

            if probs[l] < 1:
                small.append(l)
            else:
                large.append(l)

        while large:
            probs[large.pop()] = Decimal(1)

        while small:
            probs[small.pop()] = Decimal(1)

        f_probs = [float(d) for d in probs]
        return cls(f_probs, alias)

    def sample(self) -> int:
        i = random.randint(0, len(self.probs) - 1)
        u = random.uniform(0.0, 1.0)

        if self.probs[i] >= u:
            return i
        else:
            return self.alias[i]
