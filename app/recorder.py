import asyncio, os, sqlite3, time
from .detector import opportunities

DB=os.getenv('DB_PATH','/data/scanner.db')
INTERVAL=float(os.getenv('RECORD_INTERVAL_SEC','5'))

def init():
    os.makedirs(os.path.dirname(DB) or '.',exist_ok=True)
    con=sqlite3.connect(DB); con.execute('''CREATE TABLE IF NOT EXISTS opportunities(ts REAL,symbol TEXT,buy_exchange TEXT,buy_price REAL,sell_exchange TEXT,sell_price REAL,gross_pct REAL,net_bps REAL,score REAL)'''); con.execute('CREATE INDEX IF NOT EXISTS idx_opp_ts ON opportunities(ts)'); con.commit(); con.close()

def write(rows):
    con=sqlite3.connect(DB)
    con.executemany('INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?)',[(x['ts'],x['symbol'],x['buy_exchange'],x['buy_price'],x['sell_exchange'],x['sell_price'],x['gross_edge_pct'],x['estimated_net_bps'],x['score']) for x in rows])
    con.commit(); con.close()

async def recorder_loop():
    init()
    while True:
        try:
            rows=opportunities(50)
            if rows: write(rows)
        except Exception as e: print('recorder',repr(e))
        await asyncio.sleep(INTERVAL)
