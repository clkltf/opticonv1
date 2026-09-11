import asyncio, json, time, os
import aiohttp, websockets
from .state import state, Quote

BINANCE_WS='wss://stream.binance.com:9443/ws/!ticker@arr'
BYBIT_REST='https://api.bybit.com/v5/market/instruments-info?category=spot&limit=1000'
BYBIT_WS='wss://stream.bybit.com/v5/public/spot'
OKX_WS='wss://ws.okx.com:8443/ws/v5/public'
DEPTH_LIMIT=int(os.getenv('ORDERBOOK_SYMBOL_LIMIT','120'))
bybit_books={}

async def http_json(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=20) as r:
            r.raise_for_status(); return await r.json()

async def binance():
    while True:
        try:
            async with websockets.connect(BINANCE_WS,ping_interval=20,max_size=16_000_000) as ws:
                async for raw in ws:
                    data=json.loads(raw)
                    for x in data if isinstance(data,list) else []:
                        s=x.get('s','')
                        if not s.endswith('USDT'): continue
                        last=float(x.get('c') or 0); bid=float(x.get('b') or last); ask=float(x.get('a') or last)
                        if last>0: state.update(Quote('binance',s,last,bid,ask,float(x.get('q') or 0),time.time()))
        except Exception as e:
            print('binance reconnect',repr(e)); await asyncio.sleep(2)

async def binance_depth():
    while True:
        try:
            rows=await http_json('https://api.binance.com/api/v3/ticker/24hr')
            syms=sorted([x for x in rows if x.get('symbol','').endswith('USDT')],key=lambda x:float(x.get('quoteVolume') or 0),reverse=True)
            syms=[x['symbol'].lower() for x in syms[:DEPTH_LIMIT]]
            if not syms: await asyncio.sleep(5); continue
            streams='/'.join(f'{s}@depth20@100ms' for s in syms)
            url='wss://stream.binance.com:9443/stream?streams='+streams
            async with websockets.connect(url,ping_interval=20,max_size=16_000_000) as ws:
                async for raw in ws:
                    d=json.loads(raw).get('data',{}); s=d.get('s','')
                    q=state.quotes.get(s,{}).get('binance')
                    if not q: continue
                    q.bids=[[float(a),float(b)] for a,b in d.get('bids',[])]; q.asks=[[float(a),float(b)] for a,b in d.get('asks',[])]
        except Exception as e:
            print('binance depth reconnect',repr(e)); await asyncio.sleep(3)

async def bybit_symbols():
    data=await http_json(BYBIT_REST)
    return [x['symbol'] for x in data['result']['list'] if x.get('quoteCoin')=='USDT' and x.get('status')=='Trading']

def apply_bybit_book(symbol,d):
    book=bybit_books.setdefault(symbol,{'b':{},'a':{}})
    if d.get('u') is not None and d.get('type')=='snapshot': book={'b':{},'a':{}}; bybit_books[symbol]=book
    for side,key in [('b','b'),('a','a')]:
        for price,size in d.get(side,[]):
            p=float(price); q=float(size)
            if q==0: book[key].pop(p,None)
            else: book[key][p]=q
    q=state.quotes.get(symbol,{}).get('bybit')
    if q:
        q.bids=sorted([[p,s] for p,s in book['b'].items()],reverse=True)[:50]
        q.asks=sorted([[p,s] for p,s in book['a'].items()])[:50]

async def bybit_chunk(symbols):
    while True:
        try:
            async with websockets.connect(BYBIT_WS,ping_interval=20,max_size=8_000_000) as ws:
                for i in range(0,len(symbols),10):
                    await ws.send(json.dumps({'op':'subscribe','args':[f'tickers.{s}' for s in symbols[i:i+10]]})); await asyncio.sleep(.05)
                for i in range(0,min(len(symbols),DEPTH_LIMIT),10):
                    await ws.send(json.dumps({'op':'subscribe','args':[f'orderbook.50.{s}' for s in symbols[i:i+10]]})); await asyncio.sleep(.05)
                async for raw in ws:
                    msg=json.loads(raw); d=msg.get('data') or {}
                    if msg.get('topic','').startswith('orderbook.'):
                        s=d.get('s',''); apply_bybit_book(s,d); continue
                    if isinstance(d,list): d=d[0] if d else {}
                    s=d.get('symbol','')
                    if not s: continue
                    last=float(d.get('lastPrice') or 0); bid=float(d.get('bid1Price') or last); ask=float(d.get('ask1Price') or last)
                    if last>0: state.update(Quote('bybit',s,last,bid,ask,float(d.get('turnover24h') or 0),time.time()))
        except Exception as e:
            print('bybit reconnect',repr(e)); await asyncio.sleep(2)

async def bybit():
    while True:
        try:
            syms=await bybit_symbols()
            await asyncio.gather(*(bybit_chunk(syms[i:i+80]) for i in range(0,len(syms),80)))
        except Exception as e:
            print('bybit bootstrap',repr(e)); await asyncio.sleep(5)

async def okx_symbols():
    data=await http_json('https://www.okx.com/api/v5/public/instruments?instType=SPOT')
    return [x['instId'] for x in data.get('data',[]) if x.get('quoteCcy')=='USDT' and x.get('state')=='live']

async def okx_chunk(symbols):
    while True:
        try:
            async with websockets.connect(OKX_WS,ping_interval=20,max_size=8_000_000) as ws:
                args=[{'channel':'tickers','instId':s} for s in symbols]
                for i in range(0,len(args),80): await ws.send(json.dumps({'op':'subscribe','args':args[i:i+80]})); await asyncio.sleep(.1)
                for i in range(0,min(len(symbols),DEPTH_LIMIT),40):
                    await ws.send(json.dumps({'op':'subscribe','args':[{'channel':'books5','instId':s} for s in symbols[i:i+40]]})); await asyncio.sleep(.1)
                async for raw in ws:
                    msg=json.loads(raw)
                    for d in msg.get('data',[]):
                        s=d.get('instId','').replace('-',''); q=state.quotes.get(s,{}).get('okx')
                        if msg.get('arg',{}).get('channel')=='books5':
                            if q:
                                q.bids=[[float(x[0]),float(x[1])] for x in d.get('bids',[])]; q.asks=[[float(x[0]),float(x[1])] for x in d.get('asks',[])]
                            continue
                        last=float(d.get('last') or 0); bid=float(d.get('bidPx') or last); ask=float(d.get('askPx') or last)
                        if last>0: state.update(Quote('okx',s,last,bid,ask,float(d.get('volCcy24h') or 0),time.time()))
        except Exception as e:
            print('okx reconnect',repr(e)); await asyncio.sleep(2)

async def okx():
    while True:
        try:
            syms=await okx_symbols()
            await asyncio.gather(*(okx_chunk(syms[i:i+80]) for i in range(0,len(syms),80)))
        except Exception as e:
            print('okx bootstrap',repr(e)); await asyncio.sleep(5)

async def start_connectors():
    await asyncio.gather(binance(),bybit(),okx(),binance_depth())
