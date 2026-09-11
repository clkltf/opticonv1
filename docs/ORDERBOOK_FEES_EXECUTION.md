# Order book + fee-aware execution engine

## Amaç
Her borsadaki spot fırsat, yalnızca son işlem fiyatıyla değil, gerçek emir defteri (order book) üzerinden hesaplanır. Sistem mümkün olduğunda aynı anda bid/ask ve derinlik verisini kullanır.

## Her borsa için ölçülenler
- En iyi alış (best bid)
- En iyi satış (best ask)
- Bid/ask spread ve spread yüzdesi
- Fiyat seviyeleri ve miktarlar
- İstenen yatırım tutarı için kademeli (VWAP) gerçekleşme fiyatı
- Tahmini alış/satış slippage'ı
- Emir defteri derinliği
- Veri zamanı ve gecikme
- WebSocket sequence/resync durumu

## Dinamik yatırım tutarı
Kullanıcı 100 $, 1.000 $, 10.000 $ veya başka bir tutar seçebilir. Motor, o tutarın order book üzerinde gerçekten uygulanabilir olup olmadığını hesaplar. Likidite yetersizse kullanıcıya tahmini uygulanabilir maksimum tutarı ve slippage artışını gösterir.

## Komisyon motoru
Komisyonlar borsa + spot market + maker/taker + kullanıcının yapılandırılmış ücret seviyesi bazında tutulur. Varsayılan ücretler gerçek zamanlı doğrulanmamışsa sistem bunları **tahmini** olarak işaretler; kullanıcı kendi ücretini değiştirebilir. Ücret değişiklikleri config sürümüyle kaydedilir.

## Net fırsat hesabı
Tek borsa içi/çapraz borsa karşılaştırmada genel hesap:

`net_edge = executable_sell_value - executable_buy_cost - trading_fees - known_extra_costs`

Yüzde edge, gerçek uygulanabilir alış ve satış tutarları üzerinden hesaplanır. Transfer maliyeti ve transfer süresi yalnızca operasyonel olarak gerçekten kullanılacaksa ayrıca eklenir; manuel spot scanner varsayılan olarak transfer yapmaz.

## Cross-exchange senaryo
Aynı varlık için:

`Buy Exchange A ask levels -> estimated fill -> fees`
`Sell Exchange B bid levels -> estimated fill -> fees`

Aradaki net sonuç pozitif görünse bile sistem bunu **garantili arbitraj** olarak etiketlemez. Veri gecikmesi, fiyat değişimi, transfer/sermaye konumu, limitler ve gerçek execution riski ayrıca gösterilir.

## Sağlamlık kuralları
- Stale order book alarmı
- Yetersiz derinlik alarmı
- Aşırı spread filtresi
- Aykırı tek-borsa fiyatı filtresi
- Minimum notional filtresi
- Maksimum kabul edilebilir slippage
- Feed latency eşiği
- Sequence gap/resync alarmı
- Net edge için minimum güvenlik marjı

## Ücret güncelleme stratejisi
Borsa adapter'ı public fee endpointi sağlıyorsa katalog sürümüyle eşleştirilebilir. Kullanıcı hesabına özel ücret gerekiyorsa sistem API key istemeden bu bilgiyi tahmin etmez; ayarlar ekranında kullanıcı tarafından girilen maker/taker oranını kullanır. Böylece yanlış bir komisyon değeri kârlılığı olduğundan yüksek göstermez.

## UI
Her fırsat için şunlar gösterilir:
- Borsa
- Alış fiyatı ve uygulanabilir miktar
- Satış fiyatı ve uygulanabilir miktar
- Brüt fark
- Maker/taker ücretleri
- Slippage
- Net edge
- Order book derinliği
- Veri yaşı
- Tahmini uygulanabilir yatırım tutarı
- Güven seviyesi

Bu motor **manuel spot işlem** içindir ve emir göndermez.
