import asyncio, os, time, aiohttp
from .detector import opportunities

TOKEN=os.getenv('TELEGRAM_BOT_TOKEN','')
CHAT=os.getenv('TELEGRAM_CHAT_ID','')
THRESH=float(os.getenv('ALERT_SCORE','85'))
COOLDOWN=int(os.getenv('ALERT_COOLDOWN_SEC','120'))
last_sent={}

def enabled(): return bool(TOKEN and CHAT)

async def send(text):
    if not enabled(): return
    url=f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    async with aiohttp.ClientSession() as s:
        try:
            await s.post(url,json={'chat_id':CHAT,'text':text,'disable_web_page_preview':True},timeout=10)
        except Exception as e: print('telegram',repr(e))

async def alert_loop():
    while True:
        try:
            now=time.time()
            for x in opportunities(20):
                key=f"{x['symbol']}:{x['buy_exchange']}:{x['sell_exchange']}"
                if x['score']<THRESH or now-last_sent.get(key,0)<COOLDOWN: continue
                last_sent[key]=now
                text=(f"⚡ GLOBAL SPOT ALERT\n{x['symbol']}\n"
                      f"Buy {x['buy_exchange']} {x['buy_price']}\n"
                      f"Sell {x['sell_exchange']} {x['sell_price']}\n"
                      f"Gross {x['gross_edge_pct']:.3f}% | Net {x['estimated_net_bps']:.1f} bp\n"
                      f"Leader {x['leader_exchange']} {x['leader_move_10s_pct']:.2f}% | Score {x['score']}\n"
                      f"Manual research only — no order was sent.")
                await send(text)
        except Exception as e: print('alert loop',repr(e))
        await asyncio.sleep(2)
