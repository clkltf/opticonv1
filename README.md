# Global Spot Scanner

2026 odaklı, **manuel spot işlem** için gerçek zamanlı global kripto piyasa araştırma paneli.

## Uygulanan fazlar

### Phase 1 — CEX real-time discovery
- Binance Spot public WebSocket
- Bybit Spot public WebSocket
- OKX Spot public WebSocket
- Coin bazında canlı fiyat / bid / ask / 24s hacim
- Stale-feed koruması

### Phase 2 — Cross-exchange lag
- Hangi borsa hareketi önce başlattı?
- 10s / 30s / 1m / 5m / 15m momentum
- Borsalar arası ham fiyat farkı
- Gecikme ve veri tazeliği

### Phase 3 — Executable arbitrage research
- Best ask → buy / best bid → sell
- Mevcut order-book seviyeleri üzerinden tahmini executable fiyat
- Borsa komisyon varsayımları
- Slippage cezası
- Minimum likidite filtresi
- Net edge (basis points)
- Fırsat skoru

### Phase 4 — Manipulation / quality guards
- Stale quote elemesi
- Aşırı spread cezası
- Düşük likidite elemesi
- Tek borsadaki fiyat anomalilerini ayrı gösterme
- Fırsatı skorlamadan önce veri kalitesi kontrolü

### Phase 5 — DEX / on-chain discovery
- GeckoTerminal public trending-pool verisi
- Solana / Ethereum / Base / BSC ağları
- DEX fiyat, 24s hacim, fiyat değişimi ve likidite
- CEX ekranından ayrı araştırma katmanı

### Phase 6 — Backtesting
`app/backtest.py` ile CSV tabanlı fee-adjusted edge testi.

Örnek CSV başlıkları:

```text
symbol,buy_ask,sell_bid
BTCUSDT,100000,100150
```

Çalıştırma:

```bash
python -m app.backtest data/history.csv --fee-bps 10 --min-edge-bps 10
```

### Phase 7 — Live web panel
- Mobil uyumlu dashboard
- Fırsatlar
- Ani hareketler
- Cross-exchange fiyat keşfi
- DEX keşfi
- Sağlık / canlı veri durumu
- WebSocket endpoint: `/ws`

## Kurulum

```bash
git clone https://github.com/clkltf/opticonv1.git
cd opticonv1
cp .env.example .env
docker compose up -d --build
```

Panel:

```text
http://SUNUCU_IP:8080
```

## Yapılandırma

`.env` içinden:

- `MIN_NET_EDGE_BPS`
- `DEFAULT_TAKER_FEE_BPS`
- `BINANCE_FEE_BPS`
- `BYBIT_FEE_BPS`
- `OKX_FEE_BPS`
- `MIN_LIQUIDITY_USDT`
- `ORDERBOOK_SYMBOL_LIMIT`
- `DEX_ENABLED`
- `DEX_NETWORKS`

ayarlanabilir.

## Güvenlik ve işlem modeli

Bu proje **emir göndermez**. Borsa hesabı veya API anahtarı istemeden public market data ile çalışır. Kullanıcı fırsatı kendi borsasında manuel olarak değerlendirir.

Arbitraj veya momentum sinyali **kâr garantisi değildir**. Teorik fiyat farkı; komisyon, spread, slippage, transfer süresi, bakiye konumu, likidite, market impact ve fırsatın kapanması nedeniyle uygulanabilir olmayabilir.

## Veri kaynakları

Binance Spot WebSocket, Bybit V5 public Spot WebSocket ve OKX public WebSocket kullanılır. Borsaların güncel API limitleri ve stream davranışları değişebileceği için production öncesi resmi dokümantasyon kontrol edilmelidir.

## Tasarım prensibi

Amaç “en çok yükseleni bulmak” değil; **maliyet sonrası uygulanabilir edge + hareket lideri + likidite + veri kalitesi** kombinasyonunu sıralamaktır.
