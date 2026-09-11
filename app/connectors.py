import asyncio, json, time
import aiohttp, websockets
from .state import state, Quote

BINANCE_WS='wss://stream.binance.com:9443/ws/!ticker@arr'
BYBIT_REST='https://api.bybit.com/v5/market/instruments-info?category=spot'
BYBIT_WS='wss://stream.bybit.com/v5/public/spot'
OKX_WS='wss://ws.okx.com:8443/ws/v5/public'

async def binance():
    while True:
        try:
            async with websockets.connect(BINANCE_WS,ping_interval=20,max_size=8_000_000) as ws:
                async for raw in ws:
                    for x in json.loads(raw):
                        s=x.get('s','')
                        if not s.endswith('USDT'): continue
                        last=float(x.get('c') or 0); bid=float(x.get('b') or last); ask=float(x.get('a') or last)
                        if last>0: state.update(Quote('binance',s,last,bid,ask,float(x.get('q') or 0),time.time()))
        except Exception as e:
            print('binance reconnect',repr(e)); await asyncio.sleep(2)

async def bybit_symbols():
    async with aiohttp.ClientSession() as s:
        async with s.get(BYBIT_REST,timeout=20) as r:
            data=await r.json()
            return [x['symbol'] for x in data['result']['list'] if x.get('quoteCoin')=='USDT' and x.get('status')=='Trading']

async def bybit_chunk(symbols):
    while True:
        try:
            async with websockets.connect(BYBIT_WS,ping_interval=20,max_size=4_000_000) as ws:
                for i in range(0,len(symbols),10):
                    await ws.send(json.dumps({'op':'subscribe','args':[f'tickers.{s}' for s in symbols[i:i+10]]}))
                async for raw in ws:
                    msg=json.loads(raw)
                    d=msg.get('data') or {}
                    if isinstance(d,list): d=d[0] if d else {}
                    s=d.get('symbol','')
                    if not s: continue
                    last=float(d.get('lastPrice') or 0); bid=float(d.get('bid1Price') or last); ask=float(d.get('ask1Price') or last)
                    if last>0: state.update(Quote('bybit',s,last,bid,ask,float(d.get('turnover24h') or 0),time.time()))
        except Exception as e:
            print('bybit reconnect',repr(e)); await asyncio.sleep(2)

async def bybit():
    try:
        syms=await bybit_symbols()
        # Separate connections keep subscription load bounded.
        await asyncio.gather(*(bybit_chunk(syms[i:i+80]) for i in range(0,len(syms),80)))
    except Exception as e:
        print('bybit bootstrap',repr(e)); await asyncio.sleep(5)

async def okx_symbols():
    url='https://www.okx.com/api/v5/public/instruments?instType=SPOT'
    async with aiohttp.ClientSession() as s:
        async with s.get(url,timeout=20) as r:
            data=await r.json()
            return [x['instId'] for x in data.get('data',[]) if x.get('quoteCcy')=='USDT' and x.get('state')=='live']

async def okx_chunk(symbols):
    while True:
        try:
            async with websockets.connect(OKX_WS,ping_interval=20,max_size=4_000_000) as ws:
                args=[{'channel':'tickers','instId':s} for s in symbols]
                for i in range(0,len(args),80): await ws.send(json.dumps({'op':'subscribe','args':args[i:i+80]}))
                async for raw in ws:
                    msg=json.loads(raw)
                    for d in msg.get('data',[]):
                        s=d.get('instId','').replace('-','')
                        last=float(d.get('last') or 0); bid=float(d.get('bidPx') or last); ask=float(d.get('askPx') or last)
                        if last>0: state.update(Quote('okx',s,last,bid,ask,float(d.get('volCcy24h') or 0),time.time()))
        except Exception as e:
            print('okx reconnect',repr(e)); await asyncio.sleep(2)

async def okx():
    try:
        syms=await okx_symbols()
        await asyncio.gather(*(okx_chunk(syms[i:i+80]) for i in range(0,len(syms),80)))
    except Exception as e:
        print('okx bootstrap',repr(e)); await asyncio.sleep(5)

async def start_connectors():
    await asyncio.gather(binance(),bybit(),okx())
