# Global Spot Scanner

Real-time, read-only crypto spot market scanner for cross-exchange price discovery, momentum, volume anomalies and fee-aware arbitrage research.

## Scope
- Spot markets only
- Public market data only; no API keys required for the scanner
- Manual trading only; no order execution
- Binance, Bybit and OKX connectors planned in v1
- Cross-exchange lag detection
- Fee/slippage-aware opportunity scoring
- Stale-feed and liquidity guards

## Important
This software does not guarantee profit. Signals are research/monitoring outputs. Arbitrage opportunities can disappear before manual execution and may be invalid after fees, spread, slippage, transfer constraints or market impact.

## Quick start

```bash
git clone https://github.com/clkltf/opticonv1.git
cd opticonv1
cp .env.example .env
docker compose up -d --build
```

Open `http://YOUR_SERVER_IP:8080`.

## Architecture

```text
Exchange WebSockets -> normalizer -> market state -> detectors/scorer -> FastAPI -> browser
                                             |
                                             +-> symbol metadata / health
```

The scanner intentionally keeps exchange credentials out of the project. Public market streams are used for read-only monitoring.

## v1 signals
- Price move: 10s / 30s / 1m / 5m / 15m
- Volume acceleration
- Cross-exchange price lag
- Best bid/ask spread
- Estimated gross cross-exchange edge
- Configurable fee assumptions
- Conservative slippage penalty
- Feed freshness and liquidity confidence

## Roadmap
- More CEX connectors
- DEX/on-chain price discovery
- Persistent time-series history
- Telegram/Web Push alerts
- Backtesting and paper-trading mode
- Opportunity replay and execution simulator
- Symbol quality/duplicate-token protection
