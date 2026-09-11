import os, time
from .state import state

STALE_MS=float(os.getenv('STALE_MS','2500'))
FEE_BPS=float(os.getenv('DEFAULT_TAKER_FEE_BPS','10'))
MIN_EDGE_BPS=float(os.getenv('MIN_NET_EDGE_BPS','8'))


def pct(a,b):
    return ((a/b)-1)*100 if b else 0.0


def move_pct(symbol, exchange, seconds):
    hist=state.history[symbol][exchange]
    if not hist: return 0.0
    now=time.time(); target=now-seconds
    old=min(hist, key=lambda x: abs(x[0]-target))
    q=state.quotes[symbol].get(exchange)
    return pct(q.price, old[1]) if q else 0.0


def opportunities(limit=100):
    out=[]
    for symbol, venues in state.quotes.items():
        fresh={e:q for e,q in venues.items() if state.age_ms(q)<=STALE_MS and q.ask>0 and q.bid>0}
        if len(fresh)<2: continue
        buys=sorted(fresh.values(), key=lambda q:q.ask)
        sells=sorted(fresh.values(), key=lambda q:q.bid, reverse=True)
        buy,sell=buys[0],sells[0]
        if buy.exchange==sell.exchange: continue
        gross=pct(sell.bid,buy.ask)
        net_bps=gross*100-FEE_BPS*2
        lag=max((move_pct(symbol,e,10),e) for e in fresh)
        score=max(0,min(100, 50+net_bps*2+abs(lag[0])*2))
        if net_bps>=MIN_EDGE_BPS or abs(lag[0])>=1:
            out.append({
                'symbol':symbol,'buy_exchange':buy.exchange,'buy_ask':buy.ask,
                'sell_exchange':sell.exchange,'sell_bid':sell.bid,
                'gross_edge_pct':gross,'estimated_net_bps':net_bps,
                'leader_exchange':lag[1],'leader_move_10s_pct':lag[0],
                'score':round(score,1),'ts':time.time()
            })
    return sorted(out,key=lambda x:(x['score'],x['estimated_net_bps']),reverse=True)[:limit]


def movers(limit=100):
    rows=[]
    for symbol, venues in state.quotes.items():
        for e,q in venues.items():
            if state.age_ms(q)>STALE_MS: continue
            m1=move_pct(symbol,e,60)
            rows.append({'symbol':symbol,'exchange':e,'price':q.price,'bid':q.bid,'ask':q.ask,'volume_24h':q.volume_24h,'move_1m_pct':m1,'age_ms':round(state.age_ms(q))})
    return sorted(rows,key=lambda x:abs(x['move_1m_pct']),reverse=True)[:limit]
