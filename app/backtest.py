import csv, statistics, argparse

def run(path, fee_bps=10, min_edge_bps=10):
    rows=[]
    with open(path,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                gross=float(r['sell_bid'])/float(r['buy_ask'])-1
                net_bps=gross*10000-fee_bps*2
                if net_bps>=min_edge_bps:
                    rows.append(net_bps)
            except (KeyError,ValueError,ZeroDivisionError):
                continue
    if not rows: return {'trades':0,'win_rate_pct':0,'avg_net_bps':0,'total_net_bps':0}
    wins=[x for x in rows if x>0]
    return {'trades':len(rows),'win_rate_pct':round(len(wins)/len(rows)*100,2),'avg_net_bps':round(statistics.mean(rows),2),'median_net_bps':round(statistics.median(rows),2),'total_net_bps':round(sum(rows),2),'max_net_bps':round(max(rows),2),'min_net_bps':round(min(rows),2)}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('csv'); p.add_argument('--fee-bps',type=float,default=10); p.add_argument('--min-edge-bps',type=float,default=10); a=p.parse_args(); print(run(a.csv,a.fee_bps,a.min_edge_bps))
