import time
from app.detector import executable_vwap, sell_proceeds, executable_edge
from app.state import Quote

def test_buy_vwap():
    assert abs(executable_vwap([[100, 2], [101, 3]], 400, 'buy') - 100.5) < 1e-9

def test_sell_proceeds():
    assert abs(sell_proceeds([[101, 2], [100, 3]], 4) - 402) < 1e-9

def test_executable_edge_includes_fees():
    b = Quote('binance','XUSDT',100,99.9,100,100000,time.time(),asks=[[100,10]],bids=[[99.9,10]])
    s = Quote('bybit','XUSDT',101,100.9,101,100000,time.time(),asks=[[101,10]],bids=[[101,10]])
    r = executable_edge(b,s,1000)
    assert r is not None
    assert r['net_usd'] > 0
    assert r['buy_fee_usd'] > 0 and r['sell_fee_usd'] > 0
