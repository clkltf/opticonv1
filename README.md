# Global Spot Scanner

**2026 odaklı, manuel spot işlem araştırma ve gerçek-zamanlı fırsat izleme sistemi.**

> Amaç: Global spot piyasalardaki fiyat keşfini, borsalar arası gecikmeyi, uygulanabilir fiyat farkını, momentum/hacim anomalilerini, DEX/CEX ayrışmasını ve doğrulanabilir büyük cüzdan hareketlerini tek ekranda toplamak; her üretilen sinyali saklayıp daha sonra ne olduğunu ölçmek.

**Otomatik işlem yoktur.** Bu proje emir göndermez. Hiçbir sinyal kâr garantisi değildir.

---

## 1. Temel çalışma mantığı

```text
CEX WebSocket/REST       DEX + On-chain indexer
        │                         │
        └──────────┬──────────────┘
                   ▼
             NORMALIZER
                   │
                   ▼
          CANONICAL ASSET MAP
                   │
          ┌────────┴─────────┐
          ▼                  ▼
     MARKET STATE        WHALE STATE
          │                  │
          └────────┬─────────┘
                   ▼
             SIGNAL ENGINE
                   │
      ┌────────────┼─────────────┐
      ▼            ▼             ▼
  PRICE LAG     ARBITRAGE     MOMENTUM
  BREAKOUT      VOLUME        LIQUIDITY
  DEX/CEX       WHALE         ANOMALY
      │            │             │
      └────────────┼─────────────┘
                   ▼
             SIGNAL SNAPSHOT
                   │
                   ▼
              DATA STORE
                   │
          ┌────────┴─────────┐
          ▼                  ▼
     LIVE DASHBOARD       REPLAY ENGINE
                              │
                              ▼
                       WHAT HAPPENED?
```

---

# 2. Global borsa kapsamı

Sistem tek bir borsaya bağımlı tasarlanmaz. `config/exchanges.yaml` borsa kataloğudur ve adapter katmanı sayesinde yeni bir borsa ayrı modül olarak eklenebilir.

İlk global katalog:

- Binance
- Bybit
- OKX
- Coinbase
- Kraken
- KuCoin
- Gate
- MEXC
- Bitget
- HTX
- Bitfinex
- Crypto.com
- Gemini
- Bitstamp
- Upbit
- Bitrue
- WhiteBIT
- BitMart
- LBank
- Poloniex
- CoinEx
- Phemex
- BingX
- Deepcoin
- Bitunix
- BTSE
- CoinW
- Tokocrypto
- gerektiğinde diğer bölgesel/niş CEX'ler

Bu liste **"dünyadaki bütün borsalar" anlamına gelmez**. Yeni borsalar kurulabildiği, kapanabildiği, coğrafi erişim değişebildiği ve API'ler değişebildiği için sistemin doğru yaklaşımı sonsuz bir sabit liste değil, **takılabilir adapter + katalog + sağlık kontrolü** mimarisidir.

Her adapter şunları raporlar:

- API/WebSocket bağlantı durumu
- son veri zamanı
- veri gecikmesi
- sembol sayısı
- rate-limit durumu
- son hata
- API sürümü/adapter sürümü
- yeniden bağlanma sayısı

Bir borsanın API'si değişirse diğer sistem durmaz; yalnızca ilgili adapter `DEGRADED` olur.

Binance'in resmi API dokümantasyonu endpoint/stream değişikliklerini ve resmi duyuruları ayrı şekilde yayımlıyor; WebSocket bağlantılarının yaşam süresi gibi operasyonel kurallar da değişebiliyor. Bu yüzden adapter'ların otomatik health-check ve reconnect mekanizması olması zorunludur. citeturn0search0turn0search1

---

# 3. CEX market data

Her desteklenen spot market için mümkün olan en yüksek kaliteli public veri tercih edilir:

- ticker
- best bid / ask
- trades
- trade size
- order book
- order book imbalance
- spread
- depth at 10/25/50/100 bps
- 24h volume
- quote volume
- exchange timestamp
- receive timestamp
- sequence number varsa sequence

### Veri kalitesi

Her veri noktasında:

```text
exchange_timestamp
receive_timestamp
latency_ms
age_ms
sequence_ok
stale=false/true
```

tutulmalıdır.

Bu, "Bybit geride kaldı" ile "Bybit'in verisi 2 saniye gecikmiş" durumlarını ayırır.

---

# 4. Canonical asset / symbol sistemi

Borsalar aynı coin için farklı sembol kullanabilir. Bu yüzden karşılaştırma doğrudan `BTCUSDT == BTC-USDT` varsayımına dayanmaz.

Canonical kayıt:

```text
canonical_asset: BTC
base_asset: BTC
quote_asset: USDT
chain identities: ...
contract addresses: ...
exchange symbols:
  binance: BTCUSDT
  bybit: BTCUSDT
  okx: BTC-USDT
  coinbase: BTC-USDT
```

Token contract address, chain ve decimals bilgisi mümkün olduğunca kaydedilir. Bu, aynı isimli sahte/klon tokenların yanlış karşılaştırılmasını önler.

---

# 5. Fırsat motorları

## A. Cross-exchange price lag

Örneğin:

```text
Binance  +7.8%
OKX      +7.4%
Bybit    +2.1%
```

Sistem:

- lider borsayı
- ilk hareket zamanını
- diğer borsaların tepki zamanını
- fiyat farkını
- veri gecikmesini
- order-book likiditesini

ölçer.

## B. Fee-adjusted arbitrage research

```text
Gross edge
- entry fee
- exit fee
- spread
- estimated slippage
- market impact
- optional transfer cost
= estimated net edge
```

Sadece teorik spread değil, **işlem yapılabilir bid/ask ve order-book** dikkate alınır.

## C. Momentum

- 1s
- 5s
- 10s
- 30s
- 1m
- 5m
- 15m
- 1h
- 4h
- 24h

## D. Volume anomaly

Örnek:

```text
normal 1m volume: $100k
current 1m volume: $1.8m
volume multiple: 18x
```

## E. Liquidity anomaly

- spread widening
- depth collapse
- sudden liquidity removal
- abnormal order-book imbalance

## F. DEX/CEX divergence

CEX fiyatı ile DEX/pool fiyatı karşılaştırılır.

Gas/network cost, pool liquidity ve execution uncertainty ayrı tutulur.

---

# 6. Whale tracking

## Önemli gerçek

"Dünyadaki tüm balina cüzdanlarını" eksiksiz izlemek teknik olarak mümkün değildir. Public blockchainlerde adres sayısı çok büyük ve birçok adresin gerçek sahibi bilinmiyor.

Bu nedenle sistem **tüm gözlemlenebilir büyük transferleri + bilinen/labeled cüzdanları + desteklenen indexer verilerini** izlemek üzere tasarlanır.

`config/whales.yaml`:

- minimum USD transfer
- exchange inflow
- exchange outflow
- whale transfer
- whale swap
- stablecoin mint/burn
- liquidity add/remove
- accumulation
- distribution
- dormant wallet wake-up
- first-time large holder

### Whale olayları

```text
Wallet A
   ↓
$2.4M ETH transfer
   ↓
Unknown / Exchange / Smart-money label
   ↓
market context
   ↓
signal correlation
```

Her whale event:

- chain
- block
- transaction hash
- timestamp
- address
- token
- amount
- USD estimate
- direction
- counterparty
- pool/exchange
- source
- label confidence

ile saklanır.

**Private key, seed phrase veya kullanıcı hesabı bilgisi kesinlikle tutulmaz.**

---

# 7. Sinyal hafızası: sistem geçmişte ne söyledi?

Bu projenin en önemli özelliği budur.

Sistem her sinyal çıktığında yalnızca "BUY/LAG/PUMP" yazmaz. O anda gördüğü **tam piyasa fotoğrafını** saklar.

Örneğin:

```text
Signal #8f31...

2026-09-11 14:31:02 UTC
ABC/USDT

Leader: Binance
Binance: +8.42%
Bybit:   +2.13%
OKX:     +7.91%

Gross edge: 42 bps
Estimated fees: 20 bps
Estimated slippage: 7 bps
Estimated net: 15 bps
Volume: 12.6x
Spread: 8 bps
Liquidity: $4.8M
Whale context: positive
Score: 91
```

Bu kayıt **immutable signal snapshot** olarak saklanır.

---

# 8. "10.000 dolar yatırsaydım ne olurdu?" replay sistemi

Kullanıcı panelde herhangi bir geçmiş sinyali açabilir.

Örneğin:

```text
Sinyal:
ABC/USDT
Entry: $1.205
Borsa: Bybit

Hipotetik sermaye: $10,000
```

Sistem geçmiş veriyi ileri sarar:

```text
10 saniye   → $10,120
30 saniye   → $10,180
1 dakika    → $10,260
5 dakika    → $10,410
15 dakika   → $10,620
1 saat      → $10,380
4 saat      → $9,940
24 saat     → $10,870
```

Ve ayrıca:

```text
Brüt getiri
Entry fee
Exit fee
Spread
Tahmini slippage
Net hipotetik PnL
Maximum favorable excursion
Maximum adverse excursion
```

hesaplanır.

### Kritik ayrım

Panel bunu **"sen şu kadar kazandın"** diye göstermeyecek.

Şöyle gösterecek:

> **HİPOTETİK REPLAY:** Sinyal anında $10,000 ile, kayıtlı piyasa fiyatlarından ve seçilen maliyet varsayımlarıyla işlem yapılmış olsaydı tahmini sonuç.

Çünkü sistem senin gerçekten işlem yaptığını bilemez.

---

# 9. Sinyal istatistikleri

Zaman içinde sistem şunları hesaplar:

- toplam sinyal
- sinyal türüne göre başarı oranı
- ortalama forward return
- median return
- fee-adjusted return
- win rate
- loss rate
- average win
- average loss
- maximum adverse excursion
- maximum favorable excursion
- sinyalin ortalama ömrü
- borsa bazında performans
- coin büyüklüğüne göre performans
- volatilite rejimine göre performans
- BTC bull/bear/sideways rejiminde performans

Böylece örneğin:

> "5 dakikalık cross-exchange lag sinyalleri son 90 günde ücret sonrası ortalama ne yaptı?"

gibi sorular cevaplanabilir.

Geçmiş performans gelecekteki sonucu garanti etmez.

---

# 10. 200 GB disk stratejisi

200 GB diski tek bir tabloya ham WebSocket mesajları doldurarak tüketmek yerine katmanlı depolama kullanılır.

## Hot data

Son günlerin:

- quotes
- trades
- order books
- signals
- whale events

## Warm data

- 1s/5s/10s/30s/1m candle
- derived metrics
- signal outcomes

## Cold/archive data

- sıkıştırılmış raw event arşivi
- Parquet/partitioned dosyalar
- günlük/aylık bölümler

`config/retention.yaml` ile süreler değiştirilebilir.

Önerilen varsayılanlar:

```text
raw events          30 gün
trades              90 gün
order books         14 gün
quotes              180 gün
candles             5 yıl
signals             10 yıl
signal outcomes     10 yıl
whale events        10 yıl
```

Gerçek disk tüketimi aktif borsa, sembol sayısı, order-book derinliği ve kayıt frekansına bağlıdır. İlk hafta disk kullanımını ölçmeden 200 GB'ın kesin olarak yeterli olduğu varsayılmamalıdır.

---

# 11. Ayarlanabilir bütün önemli parametreler

`.env` ve `config/*.yaml` üzerinden:

### Market

- enabled exchanges
- symbol allowlist/denylist
- quote currencies
- minimum volume
- minimum liquidity
- maximum spread
- stale timeout
- order-book depth
- sampling intervals

### Arbitrage

- maker/taker fee
- minimum gross edge
- minimum net edge
- slippage model
- transfer cost
- minimum executable USD

### Momentum

- time windows
- minimum price move
- volume multiplier
- breakout thresholds
- score weights

### Whale

- minimum USD transfer
- chain list
- known wallets
- exchange labels
- smart-money labels
- event types

### Storage

- retention periods
- compression
- raw event retention
- sampling
- outcome windows
- paper-trade notional

Hiçbir secret değer GitHub'a yazılmamalıdır.

---

# 12. API değişikliklerine dayanıklılık

Her exchange connector şu arayüzü hedefler:

```text
connect()
disconnect()
subscribe_symbols()
subscribe_ticker()
subscribe_trades()
subscribe_orderbook()
normalize_event()
health()
```

Connector katmanı core detector'dan ayrıdır.

Bu sayede:

```text
Binance API değişti
        ↓
Binance adapter güncellenir
        ↓
normalizer aynı kalır
        ↓
signal engine aynı kalır
        ↓
UI aynı kalır
```

Her connector için:

- reconnect
- exponential backoff
- ping/pong
- sequence gap detection
- resync
- rate-limit awareness
- schema validation
- error logging

olmalıdır.

Örneğin Binance WebSocket dokümanı 24 saatlik bağlantı yaşam süresi ve ping/pong davranışı gibi ayrıntıları açıkça tanımlar; bunlar adapter seviyesinde ele alınmalıdır. citeturn0search1

---

# 13. Sağlık paneli

Panelde her borsa:

```text
BINANCE   🟢 LIVE   42ms
BYBIT     🟢 LIVE   51ms
OKX       🟢 LIVE   46ms
KRAKEN    🟡 DEGRADED
MEXC      🔴 OFFLINE
```

gibi görünmelidir.

Ayrıca:

- son event
- son başarılı reconnect
- son hata
- event rate
- latency p50/p95/p99
- stale ratio
- sequence gaps

gösterilir.

---

# 14. Alarm mantığı

Alarm yalnızca fiyat yüzdesine göre tetiklenmez.

Örnek yüksek kaliteli alarm:

```text
PRICE MOVE        +5.8%
VOLUME             11.4x
LIQUIDITY          HIGH
SPREAD             6 bps
CROSS-EXCHANGE     +0.42%
DATA AGE           48ms
WHALE CONTEXT      POSITIVE
SCORE              93/100
```

Düşük kaliteli alarm:

```text
PRICE MOVE        +18%
VOLUME             0.8x
LIQUIDITY          LOW
SPREAD             480 bps
DATA AGE           3.2s
```

ikinci durumda sistem bunu **manipülasyon/kalitesiz fırsat** olarak ayırmalıdır.

---

# 15. DEX / on-chain kapsamı

Desteklenecek ağ ailesi:

- Ethereum
- Solana
- Base
- Arbitrum
- Optimism
- BSC
- Avalanche
- Polygon
- Tron
- Sui
- Aptos

DEX tarafında:

- pool price
- pool liquidity
- swap volume
- buy/sell pressure
- liquidity add/remove
- large swaps
- CEX/DEX spread

izlenir.

On-chain verinin tamamı tek bir public API'den gelmez; zincir/indexer/pool adapter'ları gerektiğinde ayrı ayrı yapılandırılmalıdır.

---

# 16. Kurulum

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

Log:

```bash
docker compose logs -f
```

Durum:

```bash
docker compose ps
```

---

# 17. Production önerisi

Ubuntu sunucuda:

```text
Internet
   │
Nginx / Caddy
   │
FastAPI
   │
┌──┴───────────────┐
│                  │
Market workers   API/UI
│
├── CEX adapters
├── DEX adapters
├── Whale indexers
├── Signal engine
├── Recorder
└── Outcome engine
        │
   Data storage
```

İlk kurulumdan sonra:

1. Disk kullanımını ölç.
2. Her exchange'in health durumunu kontrol et.
3. Sembol eşleşmelerini doğrula.
4. Gerçek order-book ile executable fiyatı kontrol et.
5. Sinyal replay sonuçlarını doğrula.
6. Paper-trading ile gözlemle.
7. Manuel işlem kararını ancak kullanıcı verir.

---

# 18. Güvenlik

- API key gerekmez.
- Public market data ile çalışır.
- Trading permission kullanılmaz.
- Private key/seed phrase saklanmaz.
- `.env` GitHub'a gönderilmez.
- Secret değerler environment/secret manager üzerinden sağlanır.
- Web paneli internete açık bırakılacaksa authentication ve HTTPS kullanılmalıdır.

---

# 19. Gerçekçilik / risk

Bu sistem bir "para basma makinesi" değildir.

Arbitraj fırsatlarının önemli kısmı:

- ücret
- spread
- slippage
- order-book impact
- transfer gecikmesi
- bakiye konumu
- API latency
- rate limits
- market movement
- coin contract riskleri
- borsa erişim/withdrawal kısıtları

nedeniyle teorik olarak görünen edge'den daha düşük gerçekleşebilir.

Bu nedenle sistemin ana metriği **raw spread değil, maliyet sonrası ve veri kalitesi doğrulanmış edge** olmalıdır.

---

# 20. Roadmap / maintenance

Yeni bir exchange eklemek:

1. `config/exchanges.yaml` içine kayıt ekle.
2. Native WebSocket/REST adapter yaz.
3. Normalizer testlerini ekle.
4. Symbol mapping testlerini ekle.
5. Health/reconnect testini ekle.
6. Small-symbol canary ile production'a al.
7. Sinyal ve replay sonuçlarını karşılaştır.

API değişikliği:

1. Resmi API changelogunu kontrol et.
2. Adapter'ı güncelle.
3. Schema fixture testlerini çalıştır.
4. Reconnect/sequence testini çalıştır.
5. Canary exchange olarak aç.
6. Health panelini kontrol et.
7. Sonra `enabled=true` yap.

Binance gibi borsalar resmi API dokümantasyonunda endpoint/stream değişikliklerini ve duyuruları yayınlıyor; sistem bu yüzden adapter izolasyonu üzerine kurulmuştur. citeturn0search0

---

# 21. Projenin hedefi

Bu projenin nihai hedefi şudur:

> **Global spot piyasayı mümkün olduğunca geniş biçimde gözlemle → gerçek zamanlı anomalileri yakala → uygulanabilir maliyet sonrası edge'i hesapla → balina/on-chain bağlamını ekle → sinyali immutable olarak kaydet → gelecekte ne olduğunu ölç → hangi sinyallerin gerçekten işe yaradığını istatistiksel olarak ayır.**

Sistem kullanıcı adına işlem yapmaz.

**Scanner karar desteğidir; işlem kararı kullanıcıya aittir.**
