# Historical data model

The system should preserve the evidence needed to answer: **"What did the scanner see, what signal did it emit, and what happened afterward?"**

## Core entities

### market_event
- event_id
- exchange
- symbol
- canonical_asset
- market_type (spot)
- event_type (trade/ticker/orderbook)
- exchange_timestamp
- receive_timestamp
- local_timestamp
- bid / ask / last
- bid_size / ask_size
- price / quantity for trades
- sequence_id when supplied
- raw_payload_hash

### orderbook_snapshot
- exchange
- symbol
- timestamp
- bids / asks (compressed JSON or columnar storage)
- depth_usd_10bps / 50bps / 100bps
- spread_bps
- imbalance

### signal
Every emitted signal gets an immutable ID and the complete state used to calculate it:
- signal_id
- created_at
- signal_type
- symbol / canonical_asset
- leader_exchange
- observed_exchanges
- entry_exchange / entry_price / entry_side
- reference_price
- gross_edge_bps
- estimated_fees_bps
- estimated_slippage_bps
- estimated_net_edge_bps
- liquidity_usd
- spread_bps
- volume_multiple
- momentum fields
- whale context
- data_quality score
- confidence score
- configuration_version
- detector_version

### signal_outcome
The outcome is a **hypothetical replay**, not a claim that the user traded:
- signal_id
- horizon_seconds
- exit_timestamp
- executable_exit_price when available
- raw_return_pct
- fee_adjusted_return_pct
- slippage_adjusted_return_pct
- hypothetical_pnl_usd
- hypothetical_equity_usd
- max_favorable_excursion
- max_adverse_excursion
- reached_target flags
- invalidated flag

For example, if a signal says `BUY ABC/USDT`, the UI can calculate what a hypothetical $10,000 notional would have been worth after 1m, 5m, 15m, 1h, 4h and 24h using recorded market data and configured costs.

It must label this clearly as **paper/replay performance**. It must never imply that an actual order was placed.

## Whale entities

### whale_wallet
- chain
- address
- label
- tags
- first_seen
- last_seen
- source
- confidence

### whale_event
- event_id
- chain
- block_number
- tx_hash
- timestamp
- wallet/address
- token
- amount
- usd_value_estimate
- direction
- counterparty
- exchange/pool if known
- event_type
- source

## Storage strategy

Use hot structured tables for recent data and compressed partitioned files for older raw events. Partition by date, exchange and symbol/chain. Keep derived candles/signals much longer than raw ticks.

Do not store secrets, API keys, private keys or seed phrases in the database.
