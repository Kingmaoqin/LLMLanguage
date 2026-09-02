from __future__ import annotations

import math
import random
from collections import Counter
from typing import Iterable, List, Sequence, Tuple


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def sample_sd(values: Sequence[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def bootstrap_ci(values: Sequence[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 20260602) -> Tuple[float, float]:
    vals = list(values)
    if not vals:
        return 0.0, 0.0
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [vals[rng.randrange(len(vals))] for _ in vals]
        boots.append(mean(sample))
    boots.sort()
    lo = boots[int((alpha / 2) * (len(boots) - 1))]
    hi = boots[int((1 - alpha / 2) * (len(boots) - 1))]
    return lo, hi


def sign_test_pvalue(deltas: Sequence[float]) -> float | None:
    nonzero = [d for d in deltas if abs(d) > 1e-12]
    n = len(nonzero)
    if n == 0:
        return None
    positives = sum(1 for d in nonzero if d > 0)
    k = min(positives, n - positives)
    cdf = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * cdf)


def benjamini_hochberg(pvalues: Sequence[float | None]) -> List[float | None]:
    indexed = [(i, p) for i, p in enumerate(pvalues) if p is not None]
    m = len(indexed)
    adjusted: List[float | None] = [None for _ in pvalues]
    if m == 0:
        return adjusted
    ranked = sorted(indexed, key=lambda item: item[1])
    prev = 1.0
    for rank_from_end, (i, p) in enumerate(reversed(ranked), start=1):
        rank = m - rank_from_end + 1
        value = min(prev, p * m / rank)
        adjusted[i] = min(value, 1.0)
        prev = value
    return adjusted


def median_sequence(sequences: Sequence[str]) -> str:
    if not sequences:
        return ""
    counts = Counter(sequences)
    return counts.most_common(1)[0][0]

