import json
import sys

from metrics.format import percent
from metrics.rates import per_second


def main(path: str) -> int:
    with open(path) as f:
        windows = json.load(f)
    rates = [per_second(w["events"], w["window_s"]) for w in windows]
    busiest = max(rates)
    for w, rate in zip(windows, rates):
        share = rate / busiest if busiest else 0
        print(f"{w['name']}: {rate:.2f}/s ({percent(share)} of busiest)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
