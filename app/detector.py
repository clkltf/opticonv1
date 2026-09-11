import os, time, statistics
from .state import state

STALE_MS=float(os.getenv('STALE_MS','3000'))
DEFAULT_FEE_BPS=float(os.getenv('DEFAULT_TAKER_FEE_BPS','10'))
MIN_EDGE_BPS=float(os.getenv('MIN_NET_EDGE_BPS','10'))
MIN_LIQ=float(os.getenv('MIN_LIQUIDITY_USDT','25000'))
NOTIONAL=float(os.getenv('TEST_NOTIONAL_USDT','1000'))

FEES={'binance':float(os.getenv('BINANCE_FEE_BPS',DEFAULT_FEE_BPS)),'bybit':float(os.getenv('BYBIT_FEE_BPS',DEFAULT_FEE_BPS)),'okx':float(os.getenv('OKX_FEE_BPS',DEFAULT_FEE_BPS))}

def pct(a,b): return ((a/b)-1)*100 if b else 0.0

def move_pct(symbol, exchange, seconds):
    hist=state.history[symbol][exchange]
    if not hist: return 0.0
    target=time.time()-seconds
    candidates=[x for x in hist if x[0]<=target]
    old=candidates[-1] if candidates else hist[0]
    q=state.quotes[symbol].get(exchange)
    return pct(q.price,old[1]) if q else 0.0

def book_cost(levels, quote_amount, side):
    if not levels: return None
    remaining=quote_amount; base=0.0; spent=0.0
    for p,q in levels:
        p=float(p); q=float(q)
        if p<=0 or q<=0: continue
        take=min(q,remaining/p)
        base+=take; spent+=take*p; remaining-=take*p
        if remaining<=1e-9: break
    if remaining>1e-6 or base<=0: return None
    return spent/base if side=='buy' else spent/base

def depth_liquidity(q):
    return sum(float(p)*float(sz) for p,sz in (q.bids[:20]+q.asks[:20]))

def executable_edge(buy,sell,notional=NOTIONAL):
    buy_px=book_cost(buy.asks,notional,'buy') or buy.ask
    sell_px=book_cost(sell.bids,notional,'sell') or sell.bid
    gross=pct(sell_px,buy_px)
    fee=FEES.get(buy.exchange,DEFAULT_FEE_BPS)+FEES.get(sell.exchange,DEFAULT_FEE_BPS)
    liq=min(depth_liquidity(buy),depth_liquidity(sell))
    slippage_penalty=0.0 if buy.asks and sell.bids else 8.0
    net_bps=gross*100-fee-slippage_penalty
    return buy_px,sell_px,gross,net_bps,liq,slippage_penalty

def quality_score(gross,net_bps,liq,leader_move,lag_seconds,spread):
    score=40.0
    score+=min(25,max(0,net_bps/4))
    score+=min(15,max(0,abs(leader_move)*2))
    score+=min(10,max(0,(liq/MIN_LIQ)*2))
    score+=min(5,max(0,lag_seconds/2))
    if spread>0.5: score-=10
    if liq<MIN_LIQ: score-=15
    return round(max(0,min(100,score)),1)

def opportunities(limit=100):
    out=[]
    for symbol,venues in state.quotes.items():
        fresh={e:q for e,q in venues.items() if state.age_ms(q)<=STALE_MS and q.ask>0 and q.bid>0}
        if len(fresh)<2: continue
        for buy in fresh.values():
            for sell in fresh.values():
                if buy.exchange==sell.exchange: continue
                bp,sp,gross,net_bps,liq,slip=executable_edge(buy,sell)
                if liq<MIN_LIQ and not (buy.asks and sell.bids): continue
                moves={e:move_pct(symbol,e,10) for e in fresh}
                leader=max(moves,key=lambda e:abs(moves[e]))
                leader_move=moves[leader]
                spread=pct(buy.ask,buy.bid) if buy.bid else 0
                lag_seconds=max(0,(time.time()-fresh[leader].ts))
                score=quality_score(gross,net_bps,liq,leader_move,lag_seconds,spread)
                if net_bps>=MIN_EDGE_BPS or (abs(leader_move)>=1 and score>=60):
                    out.append({'symbol':symbol,'buy_exchange':buy.exchange,'buy_price':bp,'sell_exchange':sell.exchange,'sell_price':sp,'gross_edge_pct':round(gross,4),'estimated_net_bps':round(net_bps,2),'slippage_penalty_bps':slip,'liquidity_usdt':round(liq,2),'leader_exchange':leader,'leader_move_10s_pct':round(leader_move,3),'score':score,'fresh_ms':round(max(state.age_ms(buy),state.age_ms(sell))),'manual_only':True,'ts':time.time()})
    return sorted(out,key=lambda x:(x['score'],x['estimated_net_bps']),reverse=True)[:limit]

def movers(limit=100):
    rows=[]
    for symbol,venues in state.quotes.items():
        for e,q in venues.items():
            age=state.age_ms(q)
            if age>STALE_MS: continue
            moves={s:move_pct(symbol,e,s) for s in (10,30,60,300,900)}
            rows.append({'symbol':symbol,'exchange':e,'price':q.price,'bid':q.bid,'ask':q.ask,'spread_pct':round(pct(q.ask,q.bid),4) if q.bid else 0,'volume_24h':q.volume_24h,'move_10s_pct':round(moves[10],3),'move_30s_pct':round(moves[30],3),'move_1m_pct':round(moves[60],3),'move_5m_pct':round(moves[300],3),'move_15m_pct':round(moves[900],3),'depth_usdt':round(depth_liquidity(q),2),'age_ms':round(age)})
    return sorted(rows,key=lambda x:max(abs(x['move_10s_pct']),abs(x['move_1m_pct']),abs(x['move_5m_pct'])),reverse=True)[:limit]

def cross_exchange(limit=100):
    out=[]
    for symbol,venues in state.quotes.items():
        fresh={e:q for e,q in venues.items() if state.age_ms(q)<=STALE_MS and q.bid>0 and q.ask>0}
        if len(fresh)<2: continue
        rows=[]
        for e,q in fresh.items(): rows.append({'exchange':e,'price':q.price,'bid':q.bid,'ask':q.ask,'move_10s':move_pct(symbol,e,10),'age_ms':round(state.age_ms(q))})
        low=min(fresh.values(),key=lambda q:q.ask); high=max(fresh.values(),key=lambda q:q.bid)
        if low.exchange!=high.exchange:
            out.append({'symbol':symbol,'buy_exchange':low.exchange,'buy_ask':low.ask,'sell_exchange':high.exchange,'sell_bid':high.bid,'raw_spread_pct':round(pct(high.bid,low.ask),4),'venues':rows})
    return sorted(out,key=lambda x:x['raw_spread_pct'],reverse=True)[:limit]
