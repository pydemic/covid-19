import re
from functools import lru_cache

import numpy as np

N_RE = re.compile(r'(-?)(\d+)(\.\d{,2})?\d*')


def fmt(n):
    """
    Heuristically choose best format option for number.
    """

    try:
        return ', '.join(map(fmt, n))
    except TypeError:
        pass

    m = abs(n)
    if m < 0.001:
        return '%.2e' % n
    elif 0.001 <= m < 1000:
        if isinstance(n, int):
            return str(n)
        return f'{float(n):.2f}'
    elif 1000 <= m < 100_000:
        return _fmt_aux(n)
    elif 100_000 <= m < 1_000_000_000:
        return _fmt_aux(n / 1e6, 'mi')
    elif 1_000_000_000 <= m < 1_000_000_000_000:
        return _fmt_aux(n / 1e9, 'bi')
    else:
        return '%e' % n


def _fmt_aux(n, suffix=''):
    m = N_RE.match(str(n))
    sign, number, decimal = m.groups()
    return sign + _fix_int(number, 3) + (decimal or '') + suffix


def _fix_int(s, n):
    return ','.join(map(''.join, rpartition(s, n)))


def rpartition(seq, n):
    """
    Partition sequence in groups of n starting from the end of sequence.
    """
    seq = list(seq)
    out = []
    while seq:
        new = []
        for _ in range(n):
            if not seq:
                break
            new.append(seq.pop())
        out.append(new[::-1])
    return out[::-1]


def pc(n):
    """
    Write number as percentages.
    """
    return fmt(100 * n) + '%'


def pm(n):
    """
    Write number as parts per thousand.
    """
    return fmt(1000 * n) + '‰'


def p10k(n):
    """
    Write number as parts per ten thousand.
    """
    return fmt(10000 * n) + '‱'


def interpolant(x, y):
    """
    Creates a linear interpolant for the given function passed as sequences of
    x, y points.
    """
    x = np.array(x)
    y = np.array(y)

    @lru_cache
    def fn(t):
        return np.interp(t, x, y)

    return fn
