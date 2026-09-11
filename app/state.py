import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class Quote:
    exchange: str
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    ts: float

class MarketState:
    def __init__(self, max_history=180):
        self.quotes: Dict[str, Dict[str, Quote]] = defaultdict(dict)
        self.history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_history)))

    def update(self, q: Quote):
        self.quotes[q.symbol][q.exchange] = q
        self.history[q.symbol][q.exchange].append((q.ts, q.price, q.volume_24h))

    def snapshot(self):
        return {s: {e: asdict(q) for e, q in venues.items()} for s, venues in self.quotes.items()}

    def age_ms(self, q: Quote) -> float:
        return max(0.0, (time.time() - q.ts) * 1000)

state = MarketState()
