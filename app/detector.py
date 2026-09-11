import os, time
from .state import state

STALE_MS = float(os.getenv('STALE_MS', '3000'))
DEFAULT_FEE_BPS = float(os.getenv('DEFAULT_TAKER_FEE_BPS', '10'))
MIN_EDGE_BPS = float(os.getenv('MIN_NET_EDGE_BPS', '10'))
MIN_LIQ = float(os.getenv('MIN_LIQUIDITY_USDT', '25000'))
NOTIONAL = float(os.getenv('DEFAULT_NOTIONAL_USDT', '1000'))
FEES = {
    'binance': float(os.getenv('BINANCE_FEE_BPS', DEFAULT_FEE_BPS)),
    'bybit': float(os.getenv('BYBIT_FEE_BPS', DEFAULT_FEE_BPS)),
    'okx': float(os.getenv('OKX_FEE_BPS', DEFAULT_FEE_BPS)),
}

def pct(new, old):
    return ((new / old) - 1) * 100 if old else 0.0

def move_pct(symbol, exchange, seconds):
    hist = state.history[symbol][exchange]
    if not hist: return 0.0
    target = time.time() - seconds
    old = next((x for x in reversed(hist) if x[0] <= target), hist[0])
    q = state.quotes[symbol].get(exchange)
    return pct(q.price, old[1]) if q else 0.0

def executable_vwap(levels, quote_notional, side):
    if not levels or quote_notional <= 0: return None
    remaining_quote = quote_notional
    base = 0.0
    spent = 0.0
    for price, qty in levels:
        price, qty = float(price), float(qty)
        if price <= 0 or qty <= 0: continue
        take_base = min(qty, remaining_quote / price)
        spent += take_base * price
        base += take_base
        remaining_quote -= take_base * price
        if remaining_quote <= 1e-9: break
    if remaining_quote > 1e-6 or base <= 0: return None
    return spent / base

def sell_proceeds(levels, base_amount):
    if not levels or base_amount <= 0: return None
    remaining = base_amount
    proceeds = 0.0
    for price, qty in levels:
        price, qty = float(price), float(qty)
        take = min(qty, remaining)
        proceeds += take * price
        remaining -= take
        if remaining <= 1e-12: break
    if remaining > 1e-8: return None
    return proceeds

def depth_liquidity(q):
    return sum(float(p) * float(sz) for p, sz in (q.bids[:20] + q.asks[:20]))

def executable_edge(buy, sell, notional=NOTIONAL):
    buy_vwap = executable_vwap(buy.asks, notional, 'buy') if buy.asks else buy.ask
    if buy_vwap is None: return None
    base_bought = notional / buy_vwap
    proceeds = sell_proceeds(sell.bids, base_bought) if sell.bids else base_bought * sell.bid
    if proceeds is None: return None
    buy_fee = notional * FEES.get(buy.exchange, DEFAULT_FEE_BPS) / 10000
    sell_fee = proceeds * FEES.get(sell.exchange, DEFAULT_FEE_BPS) / 10000
    net = proceeds - buy_fee - sell_fee - notional
    gross_pct = (proceeds / notional - 1) * 100
    net_bps = net / notional * 10000
    buy_slip_bps = max(0.0, (buy_vwap / buy.ask - 1) * 10000) if buy.ask else 0.0
    sell_slip_bps = max(0.0, (sell.bid / (proceeds / base_bought) - 1) * 10000) if sell.bid else 0.0
    return {'buy_vwap': buy_vwap, 'sell_vwap': proceeds / base_bought, 'gross_pct': gross_pct,
            'net_usd': net, 'net_bps': net_bps, 'buy_fee_usd': buy_fee,
            'sell_fee_usd': sell_fee, 'slippage_bps': buy_slip_bps + sell_slip_bps,
            'liquidity_usdt': min(depth_liquidity(buy), depth_liquidity(sell))}

def quality_score(net_bps, liq, leader_move, lag_seconds, spread):
    score = 50 + min(25, max(0, net_bps / 4)) + min(10, abs(leader_move) * 2)
    score += min(10, (liq / MIN_LIQ) * 2) + min(5, lag_seconds / 2)
    if spread > 0.5: score -= 10
    if liq < MIN_LIQ: score -= 15
    return round(max(0, min(100, score)), 1)

def opportunities(limit=100, notional=NOTIONAL):
    notional = max(1.0, float(notional))
    out = []
    for symbol, venues in state.quotes.items():
        fresh = {e:q for e,q in venues.items() if state.age_ms(q) <= STALE_MS and q.ask > 0 and q.bid > 0}
        if len(fresh) < 2: continue
        for buy in fresh.values():
            for sell in fresh.values():
                if buy.exchange == sell.exchange: continue
                calc = executable_edge(buy, sell, notional)
                if not calc: continue
                liq = calc['liquidity_usdt']
                if liq < MIN_LIQ: continue
                moves = {e: move_pct(symbol, e, 10) for e in fresh}
                leader = max(moves, key=lambda e: abs(moves[e]))
                spread = pct(buy.ask, buy.bid) if buy.bid else 0
                lag = max(0, time.time() - fresh[leader].ts)
                score = quality_score(calc['net_bps'], liq, moves[leader], lag, spread)
                if calc['net_bps'] >= MIN_EDGE_BPS:
                    out.append({'symbol':symbol,'buy_exchange':buy.exchange,'buy_price':calc['buy_vwap'],
                        'sell_exchange':sell.exchange,'sell_price':calc['sell_vwap'],'notional_usdt':notional,
                        'gross_edge_pct':round(calc['gross_pct'],6),'estimated_net_bps':round(calc['net_bps'],4),
                        'estimated_net_usdt':round(calc['net_usd'],6),'buy_fee_usdt':round(calc['buy_fee_usd'],6),
                        'sell_fee_usdt':round(calc['sell_fee_usd'],6),'slippage_bps':round(calc['slippage_bps'],4),
                        'liquidity_usdt':round(liq,2),'leader_exchange':leader,
                        'leader_move_10s_pct':round(moves[leader],3),'score':score,
                        'fresh_ms':round(max(state.age_ms(buy), state.age_ms(sell))),'manual_only':True,'ts':time.time()})
    return sorted(out, key=lambda x:(x['score'],x['estimated_net_bps']), reverse=True)[:limit]

def movers(limit=100):
    rows=[]
    for symbol,venues in state.quotes.items():
        for e,q in venues.items():
            if state.age_ms(q)>STALE_MS: continue
            moves={s:move_pct(symbol,e,s) for s in (10,30,60,300,900)}
            rows.append({'symbol':symbol,'exchange':e,'price':q.price,'bid':q.bid,'ask':q.ask,
                'spread_pct':round(pct(q.ask,q.bid),4) if q.bid else 0,'volume_24h':q.volume_24h,
                'move_10s_pct':round(moves[10],3),'move_30s_pct':round(moves[30],3),
                'move_1m_pct':round(moves[60],3),'move_5m_pct':round(moves[300],3),
                'move_15m_pct':round(moves[900],3),'depth_usdt':round(depth_liquidity(q),2),'age_ms':round(state.age_ms(q))})
    return sorted(rows,key=lambda x:max(abs(x['move_10s_pct']),abs(x['move_1m_pct']),abs(x['move_5m_pct'])),reverse=True)[:limit]

def cross_exchange(limit=100):
    out=[]
    for symbol,venues in state.quotes.items():
        fresh={e:q for e,q in venues.items() if state.age_ms(q)<=STALE_MS and q.bid>0 and q.ask>0}
        if len(fresh)<2: continue
        low=min(fresh.values(),key=lambda q:q.ask); high=max(fresh.values(),key=lambda q:q.bid)
        if low.exchange!=high.exchange:
            out.append({'symbol':symbol,'buy_exchange':low.exchange,'buy_ask':low.ask,'sell_exchange':high.exchange,'sell_bid':high.bid,
                        'raw_spread_pct':round(pct(high.bid,low.ask),4)})
    return sorted(out,key=lambda x:x['raw_spread_pct'],reverse=True)[:limit]
