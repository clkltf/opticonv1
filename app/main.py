import asyncio, os
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from .connectors import start_connectors
from .detector import opportunities, movers

app=FastAPI(title='Global Spot Scanner',version='1.0.0')

@app.on_event('startup')
async def startup():
    asyncio.create_task(start_connectors())

@app.get('/api/health')
def health():
    return {'ok':True,'service':'global-spot-scanner'}

@app.get('/api/opportunities')
def api_opportunities(limit:int=Query(100,ge=1,le=500)):
    return {'items':opportunities(limit)}

@app.get('/api/movers')
def api_movers(limit:int=Query(100,ge=1,le=500)):
    return {'items':movers(limit)}

@app.get('/api/summary')
def summary():
    opp=opportunities(20)
    mov=movers(20)
    return {'opportunities':len(opp),'top_opportunities':opp[:5],'top_movers':mov[:10]}

@app.get('/')
def index():
    return FileResponse('web/index.html')
