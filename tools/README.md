# 🚨 EDS Data Merger - Kullanım Kılavuzu

Bu kılavuz, EDS (Elektronik Denetleme Sistemi) verilerinizi birleştirmek için oluşturulan araçları nasıl kullanacağınızı açıklar.

## 📁 Dosya Yapısı

```
tools/
├── advanced_data_merger.py     # Ana veri birleştirici (core engine)
├── run_merger.py              # Basit command-line arayüzü
├── web_interface.html         # Offline web arayüzü (demo)
├── web_interface_backend.html # Online web arayüzü (tam özellikli)
├── web_server.py             # Flask web sunucusu
└── README.md                 # Bu dosya
```

## 🚀 3 Farklı Kullanım Yöntemi

### Yöntem 1: Command-Line (Basit) ⭐ **ÖNERİLEN**

En kolay ve hızlı yöntem:

```bash
# 1. Tools dizinine geçin
cd tools/

# 2. Basit arayüzü çalıştırın
python run_merger.py
```

**Avantajları:**
- ✅ Hiç setup gerektirmez
- ✅ Adım adım yönlendirme
- ✅ Otomatik dosya bulma
- ✅ Progress gösterimi

### Yöntem 2: Web Arayüzü (Offline)

Frontend-only demo arayüzü:

```bash
# Web arayüzünü tarayıcıda açın
open web_interface.html
```

**Not:** Bu sadece demo amaçlıdır, gerçek işlem yapmaz.

### Yöntem 3: Web Arayüzü (Online) 🌟 **EN GELİŞMİŞ**

Tam özellikli web sunucusu:

```bash
# 1. Flask gerekliliği
pip install flask

# 2. Web sunucusunu başlatın
python web_server.py

# 3. Tarayıcıda açın
open http://localhost:5000
```

**Avantajları:**
- ✅ Drag & drop dosya yükleme
- ✅ Real-time progress
- ✅ Görsel sonuç analizi
- ✅ Direkt indirme linkleri

## 📊 Veri Gereksinimleri

### Desteklenen Formatlar:
- **GeoJSON** (.geojson) - Coğrafi veri formatı
- **JSON** (.json) - Genel veri formatı  
- **CSV** (.csv) - Tablo verisi

### Beklenen Veri Yapısı:

#### GeoJSON Format:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [28.9784, 41.0082]
      },
      "properties": {
        "type": "OHITS",
        "speed_limit": 50,
        "road": "Büyükdere Caddesi",
        "city": "Istanbul"
      }
    }
  ]
}
```

#### JSON Format:
```json
[
  {
    "latitude": 41.0082,
    "longitude": 28.9784,
    "type": "OHITS",
    "speed_limit": 50,
    "road_name": "Büyükdere Caddesi",
    "city": "Istanbul"
  }
]
```

#### CSV Format:
```csv
latitude,longitude,type,speed_limit,road_name,city
41.0082,28.9784,OHITS,50,Büyükdere Caddesi,Istanbul
```

## ⚙️ Ayar Parametreleri

### Minimum Kalite Eşiği (0.1 - 1.0)
- **0.1-0.2**: Çok gevşek, tüm verileri dahil eder
- **0.3**: **ÖNERİLEN** - İyi kalite/miktar dengesi
- **0.5-0.7**: Sıkı filtreleme
- **0.8-1.0**: Sadece en kaliteli veriler

### Dublika Tespit Mesafesi (km)
- **0.05**: Şehir içi (50m)
- **0.1**: **ÖNERİLEN** - Genel kullanım (100m)
- **0.2-0.5**: Otoyol/kırsal (200-500m)

## 📤 Çıktı Formatları

İşlem sonrası şu dosyalar oluşturulur:

1. **eds_merged_data_TIMESTAMP.geojson** - Harita uygulamaları için
2. **eds_merged_data_TIMESTAMP.json** - Genel API kullanımı için
3. **eds_merged_data_TIMESTAMP.csv** - Excel/analiz için
4. **eds_merged_data_TIMESTAMP.db** - SQLite veritabanı
5. **eds_merged_data_TIMESTAMP_stats.json** - Detaylı istatistikler

## 🔧 Sorun Giderme

### "Module not found" Hatası
```bash
# Gerekli modüller yüklü değil
pip install pandas geopy  # (opsiyonel, performans için)
```

### "No files found" Hatası  
```bash
# Scraped-datas dizinini kontrol edin
ls ../scrapers/scraped-datas/
```

### Web Sunucu Bağlantı Hatası
```bash
# Flask yüklü değil
pip install flask

# Port 5000 kullanımda
python web_server.py  # Farklı port kullanacak
```

### Memory Hatası (Büyük Dosyalar)
- Dosyaları ayrı ayrı işleyin
- Kalite eşiğini artırın (0.5+)
- Sadece command-line arayüzünü kullanın

## 📈 Performans İpuçları

### Hızlandırma:
1. **Pandas kullanın**: `pip install pandas`
2. **Geopy kullanın**: `pip install geopy`
3. **SSD kullanın** büyük dosyalar için
4. **Dublika mesafesini artırın** (0.2km)

### Kalite Artırma:
1. **OSM verilerini dahil edin** (en yüksek kalite)
2. **Birden fazla kaynak** kullanın
3. **Confidence score'u kontrol edin**

## 🔗 EDS Uyarı Sistemi Entegrasyonu

İşlenmiş verileri ana uygulamada kullanmak için:

1. **GeoJSON dosyasını kopyalayın**:
   ```bash
   cp merged-output/eds_merged_data_*.geojson ../data/eds-locations.geojson
   ```

2. **Index.html'i güncelleyin**:
   - Test verilerini kaldırın
   - Gerçek GeoJSON'ı yükleyin

3. **Veri sayısını güncelleyin**:
   ```javascript
   console.log('✅ EDS verileri yüklendi:', edsLocations.length, 'kamera');
   ```

## 🆘 Destek

### Hata Raporlama:
1. Hata mesajının tam metni
2. Kullanılan komut/yöntem
3. Veri dosyalarının boyutu ve türü
4. Python version: `python --version`

### Yaygın Sorular:

**S: Hangi yöntemi kullanmalıyım?**
A: Yeni başlayanlar için `python run_merger.py` - basit ve güvenli.

**S: Veriler birleşmiyor, çok az sonuç geliyor?**
A: Kalite eşiğini düşürün (0.2), dublika mesafesini artırın (0.2km).

**S: İşlem çok yavaş?**
A: `pip install pandas geopy` ile hızlandırın, küçük dosyalarla test edin.

**S: Web arayüzü çalışmıyor?**
A: `python web_server.py` çalışıp http://localhost:5000 açın.

## 🎯 Örnek Kullanım Senaryoları

### Senaryo 1: İlk Kurulum
```bash
cd tools/
python run_merger.py
# Varsayılan ayarları kullan (Enter'a bas)
# Sonucu ../data/ klasörüne kopyala
```

### Senaryo 2: Büyük Veri Seti
```bash
python advanced_data_merger.py \
  --input-dir ../scrapers/scraped-datas \
  --min-quality 0.5 \
  --duplicate-threshold 0.15 \
  --verbose
```

### Senaryo 3: Web Demo
```bash
python web_server.py &
open http://localhost:5000
# Dosyaları drag & drop et
# Ayarları yap ve işlet
```
