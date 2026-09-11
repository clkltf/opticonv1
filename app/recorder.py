import asyncio, os, time
import psycopg
from .detector import opportunities

DB=os.getenv('DATABASE_URL','')
INTERVAL=float(os.getenv('RECORD_INTERVAL_SEC','5'))
RETENTION_DAYS=int(os.getenv('RETENTION_DAYS','30'))

SCHEMA='''CREATE TABLE IF NOT EXISTS opportunities (
 id BIGSERIAL PRIMARY KEY, ts DOUBLE PRECISION NOT NULL, symbol TEXT NOT NULL,
 buy_exchange TEXT NOT NULL, buy_price DOUBLE PRECISION NOT NULL,
 sell_exchange TEXT NOT NULL, sell_price DOUBLE PRECISION NOT NULL,
 notional_usdt DOUBLE PRECISION NOT NULL, gross_pct DOUBLE PRECISION NOT NULL,
 net_bps DOUBLE PRECISION NOT NULL, net_usdt DOUBLE PRECISION NOT NULL,
 buy_fee_usdt DOUBLE PRECISION NOT NULL, sell_fee_usdt DOUBLE PRECISION NOT NULL,
 slippage_bps DOUBLE PRECISION NOT NULL, liquidity_usdt DOUBLE PRECISION NOT NULL,
 score DOUBLE PRECISION NOT NULL)'''

def init():
    with psycopg.connect(DB) as con:
        con.execute(SCHEMA)
        con.execute('CREATE INDEX IF NOT EXISTS idx_opp_ts ON opportunities(ts)')

def write(rows):
    if not rows: return
    with psycopg.connect(DB) as con:
        con.executemany('''INSERT INTO opportunities
        (ts,symbol,buy_exchange,buy_price,sell_exchange,sell_price,notional_usdt,gross_pct,net_bps,net_usdt,buy_fee_usdt,sell_fee_usdt,slippage_bps,liquidity_usdt,score)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        [(x['ts'],x['symbol'],x['buy_exchange'],x['buy_price'],x['sell_exchange'],x['sell_price'],x['notional_usdt'],x['gross_edge_pct'],x['estimated_net_bps'],x['estimated_net_usdt'],x['buy_fee_usdt'],x['sell_fee_usdt'],x['slippage_bps'],x['liquidity_usdt'],x['score']) for x in rows])

def cleanup():
    cutoff=time.time()-RETENTION_DAYS*86400
    with psycopg.connect(DB) as con: con.execute('DELETE FROM opportunities WHERE ts < %s',(cutoff,))

async def recorder_loop():
    while True:
        try:
            init(); write(opportunities(50)); cleanup()
        except Exception as e: print('recorder',repr(e))
        await asyncio.sleep(INTERVAL)
