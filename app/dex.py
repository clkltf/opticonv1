import asyncio, os, time
import aiohttp
from .state import state

NETWORKS=[x.strip() for x in os.getenv('DEX_NETWORKS','solana,eth,base,bsc').split(',') if x.strip()]
INTERVAL=int(os.getenv('GECKOTERMINAL_INTERVAL_SEC','30'))
BASE='https://api.geckoterminal.com/api/v2'

async def fetch_network(session, network):
    url=f'{BASE}/networks/{network}/trending_pools'
    try:
        async with session.get(url,timeout=15,headers={'accept':'application/json;version=20230302'}) as r:
            if r.status!=200: return
            data=await r.json()
            rows=[]
            for item in data.get('data',[])[:50]:
                a=item.get('attributes',{})
                rows.append({'network':network,'name':a.get('name'),'address':item.get('id'),'price_usd':a.get('base_token_price_usd'),'volume_24h_usd':a.get('volume_usd',{}).get('h24'),'price_change_24h':a.get('price_change_percentage',{}).get('h24'),'liquidity_usd':a.get('reserve_in_usd'),'source':'geckoterminal','ts':time.time()})
            state.dex[network]=rows
    except Exception as e:
        print('dex',network,repr(e))

async def dex_loop():
    if os.getenv('DEX_ENABLED','true').lower()!='true': return
    while True:
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*(fetch_network(session,n) for n in NETWORKS))
        await asyncio.sleep(INTERVAL)

def dex_snapshot():
    out=[]
    for rows in state.dex.values(): out.extend(rows)
    return sorted(out,key=lambda x:float(x.get('volume_24h_usd') or 0),reverse=True)
