import re


def parse_temperature_bucket(question):
    q = question.lower()

    below_match = re.search(r"(\d{1,3})\s*°?c\s*or below", q)
    if below_match:
        return {"low": None, "high": float(below_match.group(1))}

    above_match = re.search(r"(\d{1,3})\s*°?c\s*or higher", q)
    if above_match:
        return {"low": float(above_match.group(1)), "high": None}

    single_match = re.search(r"be\s*(\d{1,3})\s*°c", q)
    if single_match:
        value = float(single_match.group(1))
        return {"low": value - 0.5, "high": value + 0.5}

    return None

from scipy.stats import norm


def probability_of_bucket(bucket, forecast_high, uncertainty_stdev=2.5):
    mean = forecast_high
    std = uncertainty_stdev

    if bucket["low"] is not None and bucket["high"] is not None:
        p = norm.cdf(bucket["high"], mean, std) - norm.cdf(bucket["low"], mean, std)
    elif bucket["low"] is not None:
        p = 1 - norm.cdf(bucket["low"], mean, std)
    elif bucket["high"] is not None:
        p = norm.cdf(bucket["high"], mean, std)
    else:
        p = 0.5

    return round(p, 4)