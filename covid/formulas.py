import numpy as np


def K(m):
    g = m.gamma_i
    s = m.sigma
    R0 = m.R0
    return 0.5 * (s + g) * (np.sqrt(1 + 4 * (R0 - 1) * s * g / (s + g) ** 2) - 1)


def T_first(m, cases, i0=1):
    k = K(m)
    g = m.gamma_i
    return 1 / k * np.log((cases / i0 * k + g) / (k + g))


def I0_(m, cases, T):
    g = m.gamma_i
    k = K(m)
    return cases / ((1 + g / k) * np.exp(k * T) - g / k)


def E0(m, i0):
    qs = m.prob_symptomatic
    k = K(m)
    return i0 * (m.gamma_i + k) / m.sigma / qs


def A0(m, i0):
    qs = m.prob_symptomatic
    return i0 * (1 - qs) / qs


def H0(m, i0, t):
    qh = m.prob_hospitalization
    gh = m.gamma_h
    g = m.gamma_i
    k = K(m)
    return qh * g * i0 / (gh + k) * (np.exp(k * t) - np.exp(-gh * t))


def C0(m, i0, t):
    qc = m.prob_icu
    qh = m.prob_hospitalization
    gh = m.gamma_h
    gc = m.gamma_c
    g = m.gamma_i
    k = K(m)
    cte = qc * qh * gh * g * i0 / ((k + gh) * (k + gc))
    t1 = np.exp(k * t)
    t2 = (gc + k) / (gh - gc) * np.exp(-gh * t)
    t3 = (gh + k) / (gh - gc) * np.exp(-gc * t)
    return cte * (t1 + t2 - t3)


def F0(m, i0, t):
    qc = m.prob_icu
    qh = m.prob_hospitalization
    qf = m.prob_fatality
    gh = m.gamma_h
    gc = m.gamma_c
    g = m.gamma_i
    k = K(m)
    cte = qc * qh * qf * g * gh * gc * i0 / ((k + gh) * (k + gc))
    t1 = (np.exp(k * t) - 1) / k
    t2 = (gc + k) / (gh * (gh - gc)) * (np.exp(-gh * t) - 1)
    t3 = (gh + k) / (gc * (gh - gc)) * (np.exp(-gc * t) - 1)
    return cte * (t1 + t2 - t3)


def R0_from_k(m, k):
    g = m.gamma_i
    s = m.sigma
    return 1 + (g + s + k) * (k / (g * s))
