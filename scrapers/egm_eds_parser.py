import requests
from bs4 import BeautifulSoup
import json
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
from typing import Dict, List, Optional
import logging

class EGMEDSParser:
    """
    EGM Elektronik Denetleme Sistemi (EDS) Harita Verilerini Parse Eden Sınıf
    
    Bu parser, EGM'nin trafik denetleme sistemlerinin lokasyon verilerini
    çekmek ve analiz etmek için kullanılır.
    """
    
    def __init__(self, headless: bool = True, wait_timeout: int = 30):
        """
        Parser'ı başlatır
        
        Args:
            headless: Tarayıcıyı görünmez modda çalıştır
            wait_timeout: Sayfa yükleme timeout süresi
        """
        self.base_url = "https://onlineislemler.egm.gov.tr/trafik/sayfalar/edsharita.aspx"
        self.session = requests.Session()
        self.wait_timeout = wait_timeout
        
        # Selenium WebDriver Ayarları
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = None
        self.eds_data = []
        
        # Logging ayarı
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def start_driver(self):
        """WebDriver'ı başlatır"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            return True
        except Exception as e:
            self.logger.error(f"WebDriver başlatılamadı: {e}")
            return False
    
    def stop_driver(self):
        """WebDriver'ı kapatır"""
        if self.driver:
            self.driver.quit()
    
    def parse_eds_map_data(self) -> List[Dict]:
        """
        EDS harita verilerini parse eder
        
        Returns:
            EDS nokta verilerini içeren liste
        """
        if not self.start_driver():
            return []
        
        try:
            self.logger.info("EGM EDS sayfası yükleniyor...")
            self.driver.get(self.base_url)
            
            # Sayfanın tam yüklenmesini bekle
            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # JavaScript harita verilerini çek
            map_data = self.extract_map_markers()
            
            # AJAX çağrılarını yakala
            ajax_data = self.capture_ajax_requests()
            
            # JSON verilerini parse et
            parsed_data = self.parse_json_data(map_data, ajax_data)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Veri parse edilirken hata: {e}")
            return []
        finally:
            self.stop_driver()
    
    def extract_map_markers(self) -> List[Dict]:
        """Harita üzerindeki marker verilerini çıkarır"""
        markers = []
        
        try:
            # JavaScript ile harita verilerini al
            script = """
            var mapData = [];
            
            // Google Maps API marker'larını kontrol et
            if (typeof google !== 'undefined' && google.maps) {
                // Google Maps marker'larını bul
                var mapDiv = document.querySelector('#map, .map-container, [id*="map"]');
                if (mapDiv) {
                    // Marker verilerini çıkar
                    mapData.push({type: 'google_maps', found: true});
                }
            }
            
            // Leaflet harita kontrolü
            if (typeof L !== 'undefined') {
                mapData.push({type: 'leaflet', found: true});
            }
            
            // Sayfa içinde gömülü JSON verilerini ara
            var scripts = document.querySelectorAll('script');
            for (var i = 0; i < scripts.length; i++) {
                var content = scripts[i].innerHTML;
                if (content.includes('latitude') || content.includes('longitude') || 
                    content.includes('coord') || content.includes('marker')) {
                    mapData.push({
                        type: 'embedded_json',
                        content: content.substring(0, 1000)
                    });
                }
            }
            
            return mapData;
            """
            
            result = self.driver.execute_script(script)
            return result if result else []
            
        except Exception as e:
            self.logger.error(f"Marker çıkarma hatası: {e}")
            return []
    
    def capture_ajax_requests(self) -> List[Dict]:
        """AJAX isteklerini yakalar"""
        ajax_data = []
        
        try:
            # Network loglarını kontrol et
            logs = self.driver.get_log('performance')
            
            for log in logs:
                message = json.loads(log['message'])
                if message['message']['method'] == 'Network.responseReceived':
                    url = message['message']['params']['response']['url']
                    if any(keyword in url.lower() for keyword in ['eds', 'harita', 'marker', 'koordinat']):
                        ajax_data.append({
                            'url': url,
                            'timestamp': log['timestamp']
                        })
                        
        except Exception as e:
            self.logger.warning(f"AJAX yakalama hatası: {e}")
        
        return ajax_data
    
    def parse_json_data(self, map_data: List[Dict], ajax_data: List[Dict]) -> List[Dict]:
        """JSON verilerini parse eder ve EDS bilgilerini çıkarır"""
        parsed_eds = []
        
        # Embedded JSON'dan koordinat verilerini çıkar
        for data in map_data:
            if data.get('type') == 'embedded_json':
                content = data.get('content', '')
                coords = self.extract_coordinates_from_text(content)
                for coord in coords:
                    parsed_eds.append({
                        'latitude': coord['lat'],
                        'longitude': coord['lng'],
                        'type': 'eds_point',
                        'source': 'embedded_json',
                        'timestamp': time.time()
                    })
        
        return parsed_eds
    
    def extract_coordinates_from_text(self, text: str) -> List[Dict]:
        """Metinden koordinat bilgilerini çıkarır"""
        coordinates = []
        
        # Regex patterns for coordinates
        patterns = [
            r'latitude["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?.*?longitude["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?',
            r'lat["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?.*?lng["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?',
            r'lat["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?.*?lon["\']?\s*:\s*["\']?(-?\d+\.?\d*)["\']?',
            r'(-?\d{1,2}\.\d+),\s*(-?\d{1,2}\.\d+)',  # Direct coordinate pairs
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                    
                    # Türkiye koordinat aralığı kontrolü
                    if 35.0 <= lat <= 43.0 and 25.0 <= lng <= 45.0:
                        coordinates.append({
                            'lat': lat,
                            'lng': lng
                        })
                except (ValueError, IndexError):
                    continue
        
        return coordinates
    
    def get_eds_categories(self) -> Dict[str, str]:
        """EDS kategori bilgilerini döndürür"""
        return {
            'OHITS': 'Ortalama Hız İhlal Tespit Sistemi',
            'KIITS': 'Kırmızı Işık İhlal Tespit Sistemi',
            'PITS': 'Park İhlal Tespit Sistemi',
            'SITS': 'Şerit İhlal Tespit Sistemi',
            'HIZ': 'Anlık Hız Denetleme',
            'MOBIL': 'Mobil Denetleme'
        }
    
    def validate_eds_data(self, data: List[Dict]) -> List[Dict]:
        """EDS verilerini doğrular ve temizler"""
        validated = []
        
        for item in data:
            # Koordinat kontrolü
            if not all(key in item for key in ['latitude', 'longitude']):
                continue
            
            lat, lng = item['latitude'], item['longitude']
            
            # Türkiye sınırları içinde mi?
            if not (35.0 <= lat <= 43.0 and 25.0 <= lng <= 45.0):
                continue
            
            # Veri formatını standartlaştır
            validated_item = {
                'id': f"eds_{len(validated) + 1}",
                'latitude': round(float(lat), 6),
                'longitude': round(float(lng), 6),
                'type': item.get('type', 'unknown'),
                'category': item.get('category', 'GENEL'),
                'city': self.get_city_from_coordinates(lat, lng),
                'timestamp': item.get('timestamp', time.time()),
                'source': item.get('source', 'unknown')
            }
            
            validated.append(validated_item)
        
        return validated
    
    def get_city_from_coordinates(self, lat: float, lng: float) -> str:
        """Koordinattan şehir bilgisini tahmin eder"""
        # Basit şehir tespiti (gerçek uygulamada reverse geocoding kullanın)
        city_coords = {
            'Istanbul': [(41.0082, 28.9784), (40.9, 29.5)],
            'Ankara': [(39.9334, 32.8597), (39.7, 33.1)],
            'Izmir': [(38.4237, 27.1428), (38.2, 27.5)],
            'Bursa': [(40.1826, 29.0669), (40.0, 29.3)],
            'Antalya': [(36.8841, 30.7056), (36.7, 31.0)]
        }
        
        for city, bounds in city_coords.items():
            if bounds[0][0] <= lat <= bounds[1][0] and bounds[0][1] <= lng <= bounds[1][1]:
                return city
        
        return 'Diger'
    
    def save_to_formats(self, data: List[Dict], base_filename: str = 'eds_data'):
        """Veriyi farklı formatlarda kaydeder"""
        timestamp = int(time.time())
        
        # JSON
        json_file = f"{base_filename}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # CSV
        if data:
            df = pd.DataFrame(data)
            csv_file = f"{base_filename}_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # GeoJSON (Harita uygulamaları için)
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        for item in data:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [item['longitude'], item['latitude']]
                },
                "properties": {k: v for k, v in item.items() if k not in ['latitude', 'longitude']}
            }
            geojson["features"].append(feature)
        
        geojson_file = f"{base_filename}_{timestamp}.geojson"
        with open(geojson_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Veriler kaydedildi: {json_file}, {csv_file}, {geojson_file}")
    
    def get_statistics(self, data: List[Dict]) -> Dict:
        """EDS verilerinin istatistiklerini çıkarır"""
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        
        stats = {
            'toplam_eds_sayisi': len(data),
            'sehir_bazinda_dagilim': df['city'].value_counts().to_dict(),
            'kategori_bazinda_dagilim': df['category'].value_counts().to_dict(),
            'koordinat_araliklari': {
                'min_latitude': df['latitude'].min(),
                'max_latitude': df['latitude'].max(),
                'min_longitude': df['longitude'].min(),
                'max_longitude': df['longitude'].max()
            }
        }
        
        return stats

# Kullanım Örneği
def main():
    """Parser'ı çalıştır ve veriyi analiz et"""
    parser = EGMEDSParser(headless=True)
    
    print("EGM EDS verilerini çekiliyor...")
    eds_data = parser.parse_eds_map_data()
    
    if eds_data:
        print(f"Toplam {len(eds_data)} EDS noktası bulundu.")
        
        # Veriyi doğrula
        validated_data = parser.validate_eds_data(eds_data)
        print(f"Doğrulanmış veri sayısı: {len(validated_data)}")
        
        # İstatistikleri göster
        stats = parser.get_statistics(validated_data)
        print("\nİstatistikler:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        
        # Veriyi kaydet
        parser.save_to_formats(validated_data)
        
    else:
        print("Veri çekilemedi. Site erişimi kontrol edilmelidir.")

if __name__ == "__main__":
    main()
