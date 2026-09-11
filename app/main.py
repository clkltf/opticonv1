import asyncio, time, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from .connectors import start_connectors
from .detector import opportunities, movers, cross_exchange
from .dex import dex_loop, dex_snapshot
from .alerts import alert_loop
from .recorder import recorder_loop
from .state import state

@asynccontextmanager
async def lifespan(app):
    tasks = [asyncio.create_task(start_connectors()), asyncio.create_task(dex_loop()),
             asyncio.create_task(alert_loop()), asyncio.create_task(recorder_loop())]
    yield
    for task in tasks: task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title='Global Spot Scanner', version='2.3.0', lifespan=lifespan)

@app.get('/api/health')
def health():
    exchanges = {}
    for symbol, venues in state.quotes.items():
        for e, q in venues.items():
            if state.age_ms(q) < 10000: exchanges[e] = exchanges.get(e, 0) + 1
    return {'ok': True, 'service': 'global-spot-scanner', 'symbols': len(state.quotes), 'live_quotes': exchanges,
            'dex_networks': list(state.dex), 'timestamp': time.time()}

@app.get('/api/opportunities')
def api_opportunities(limit:int=Query(100,ge=1,le=500), notional:float=Query(None,gt=0,le=1_000_000)):
    return {'items': opportunities(limit, notional) if notional else opportunities(limit)}

@app.get('/api/movers')
def api_movers(limit:int=Query(100,ge=1,le=500)): return {'items': movers(limit)}
@app.get('/api/cross-exchange')
def api_cross(limit:int=Query(100,ge=1,le=500)): return {'items': cross_exchange(limit)}
@app.get('/api/dex')
def api_dex(limit:int=Query(100,ge=1,le=500)): return {'items': dex_snapshot()[:limit]}
@app.get('/api/markets')
def api_markets(): return {'items': state.snapshot()}
@app.get('/api/summary')
def summary():
    opp = opportunities(20); mov = movers(20)
    return {'ts':time.time(),'symbols':len(state.quotes),'opportunities':len(opp),'top_opportunities':opp[:8],'top_movers':mov[:12],'dex_count':len(dex_snapshot())}

@app.websocket('/ws')
async def ws(websocket:WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps({'ts':time.time(),'opportunities':opportunities(20),'movers':movers(30)},separators=(',',':')))
            await asyncio.sleep(1)
    except (WebSocketDisconnect, RuntimeError): return

@app.get('/')
def index(): return FileResponse('web/index.html')
