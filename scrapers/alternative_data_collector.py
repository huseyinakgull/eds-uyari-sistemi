import requests
import json
import time
from typing import Dict, List
import logging
from dataclasses import dataclass, asdict
import sqlite3
from datetime import datetime

@dataclass
class EDSPoint:
    """EDS nokta veri yapısı"""
    id: str
    latitude: float
    longitude: float
    type: str  # OHITS, KIITS, PITS, HIZ
    city: str
    district: str
    road_name: str
    direction: str
    speed_limit: int
    status: str  # active, inactive, maintenance
    installation_date: str
    last_updated: str

class AlternativeEDSCollector:
    """
    Alternatif EDS veri toplama yöntemleri
    - Açık veri platformları
    - Crowdsourced veriler
    - Resmi API'lar
    - Topluluk veritabanları
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.logger = logging.getLogger(__name__)
        self.db_path = 'eds_database.db'
        self.init_database()
    
    def init_database(self):
        """SQLite veritabanını başlatır"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eds_points (
                id TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                type TEXT,
                city TEXT,
                district TEXT,
                road_name TEXT,
                direction TEXT,
                speed_limit INTEGER,
                status TEXT,
                installation_date TEXT,
                last_updated TEXT,
                source TEXT,
                confidence_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_from_open_data_platforms(self) -> List[EDSPoint]:
        """Açık veri platformlarından EDS verilerini toplar"""
        sources = [
            'https://data.gov.tr',  # Türkiye Açık Veri Platformu
            'https://www.harita.gov.tr',  # Harita Genel Müdürlüğü
            # Diğer belediye açık veri platformları
        ]
        
        collected_data = []
        
        # Bu bölümde gerçek API çağrıları yapılacak
        # Örnek veri yapısı:
        sample_data = [
            EDSPoint(
                id="sample_001",
                latitude=41.0082,
                longitude=28.9784,
                type="OHITS",
                city="Istanbul",
                district="Sisli",
                road_name="Buyukdere Caddesi",
                direction="N-S",
                speed_limit=50,
                status="active",
                installation_date="2023-01-15",
                last_updated=datetime.now().isoformat()
            )
        ]
        
        return sample_data
    
    def collect_from_crowdsourced_data(self) -> List[EDSPoint]:
        """Topluluk kaynaklı verilerden EDS bilgilerini toplar"""
        
        # Waze, Google Maps, navigasyon uygulamaları benzeri
        # topluluk raporlarını analiz eder
        
        crowdsourced_apis = [
            'https://api.waze.com',  # Waze API (eğer erişim varsa)
            'https://overpass-api.de/api/interpreter',  # OpenStreetMap
        ]
        
        # OpenStreetMap Overpass API örneği
        overpass_query = """
        [out:json][timeout:25];
        (
          node["highway"="speed_camera"](bbox:35,25,43,45);
          node["enforcement"="maxspeed"](bbox:35,25,43,45);
        );
        out;
        """
        
        try:
            response = self.session.post(
                'https://overpass-api.de/api/interpreter',
                data=overpass_query
            )
            
            if response.status_code == 200:
                osm_data = response.json()
                return self.parse_osm_data(osm_data)
        except Exception as e:
            self.logger.error(f"OSM veri toplama hatası: {e}")
        
        return []
    
    def parse_osm_data(self, osm_data: Dict) -> List[EDSPoint]:
        """OpenStreetMap verilerini parse eder"""
        eds_points = []
        
        for element in osm_data.get('elements', []):
            if element.get('type') == 'node':
                tags = element.get('tags', {})
                
                eds_point = EDSPoint(
                    id=f"osm_{element.get('id')}",
                    latitude=element.get('lat'),
                    longitude=element.get('lon'),
                    type=self.map_osm_to_eds_type(tags),
                    city=tags.get('addr:city', 'Unknown'),
                    district=tags.get('addr:district', 'Unknown'),
                    road_name=tags.get('highway', 'Unknown'),
                    direction=tags.get('direction', 'Unknown'),
                    speed_limit=int(tags.get('maxspeed', 0)) if tags.get('maxspeed', '').isdigit() else 0,
                    status='active',
                    installation_date='Unknown',
                    last_updated=datetime.now().isoformat()
                )
                
                eds_points.append(eds_point)
        
        return eds_points
    
    def map_osm_to_eds_type(self, tags: Dict) -> str:
        """OSM etiketlerini EDS tiplerine dönüştürür"""
        if 'speed_camera' in str(tags.values()).lower():
            return 'HIZ'
        elif 'traffic_signals' in str(tags.values()).lower():
            return 'KIITS'
        else:
            return 'GENEL'
    
    def collect_from_mobile_apps(self) -> List[EDSPoint]:
        """Mobil navigasyon uygulamalarından veri toplar"""
        
        # Bu yöntem, uygulamaların API'larını kullanarak
        # veya web scraping ile veri toplar
        
        mobile_data_sources = {
            'yandex_navigator': 'https://api.routing.yandex.net',
            'here_maps': 'https://developer.here.com/api',
            'tomtom': 'https://api.tomtom.com'
        }
        
        # Örnek implementasyon (API anahtarı gerekli)
        collected_data = []
        
        return collected_data
    
    def validate_and_merge_data(self, data_sources: List[List[EDSPoint]]) -> List[EDSPoint]:
        """Farklı kaynaklardan gelen verileri doğrular ve birleştirir"""
        all_points = []
        
        for source_data in data_sources:
            all_points.extend(source_data)
        
        # Dublicate elimination based on coordinates
        unique_points = {}
        
        for point in all_points:
            # 100 metre yakınlık kontrolü
            coord_key = f"{round(point.latitude, 4)}_{round(point.longitude, 4)}"
            
            if coord_key not in unique_points:
                unique_points[coord_key] = point
            else:
                # Confidence score'a göre en iyi veriyi seç
                existing = unique_points[coord_key]
                if self.calculate_confidence_score(point) > self.calculate_confidence_score(existing):
                    unique_points[coord_key] = point
        
        return list(unique_points.values())
    
    def calculate_confidence_score(self, point: EDSPoint) -> float:
        """Veri güvenilirlik skoru hesaplar"""
        score = 0.5  # Base score
        
        # Veri tamamlığı kontrolü
        if point.city != 'Unknown':
            score += 0.1
        if point.road_name != 'Unknown':
            score += 0.1
        if point.speed_limit > 0:
            score += 0.1
        if point.type in ['OHITS', 'KIITS', 'PITS', 'HIZ']:
            score += 0.2
        
        return score
    
    def save_to_database(self, eds_points: List[EDSPoint]):
        """EDS verilerini SQLite veritabanına kaydeder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for point in eds_points:
            point_dict = asdict(point)
            point_dict['source'] = 'multiple'
            point_dict['confidence_score'] = self.calculate_confidence_score(point)
            
            cursor.execute('''
                INSERT OR REPLACE INTO eds_points 
                (id, latitude, longitude, type, city, district, road_name, 
                 direction, speed_limit, status, installation_date, last_updated, 
                 source, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(point_dict.values()))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"{len(eds_points)} EDS noktası veritabanına kaydedildi")
    
    def export_for_applications(self, output_format: str = 'all'):
        """Uygulama geliştirme için veriyi export eder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM eds_points WHERE confidence_score > 0.6')
        rows = cursor.fetchall()
        conn.close()
        
        # Column names
        columns = ['id', 'latitude', 'longitude', 'type', 'city', 'district', 
                  'road_name', 'direction', 'speed_limit', 'status', 
                  'installation_date', 'last_updated', 'source', 'confidence_score']
        
        data = [dict(zip(columns, row)) for row in rows]
        
        if output_format in ['json', 'all']:
            with open('eds_export.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        if output_format in ['geojson', 'all']:
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [item['longitude'], item['latitude']]
                        },
                        "properties": {k: v for k, v in item.items() 
                                     if k not in ['latitude', 'longitude']}
                    } for item in data
                ]
            }
            
            with open('eds_export.geojson', 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        if output_format in ['api', 'all']:
            # REST API format
            api_format = {
                "metadata": {
                    "total_points": len(data),
                    "last_updated": datetime.now().isoformat(),
                    "coverage": "Turkey",
                    "confidence_threshold": 0.6
                },
                "eds_points": data
            }
            
            with open('eds_api_format.json', 'w', encoding='utf-8') as f:
                json.dump(api_format, f, ensure_ascii=False, indent=2)

class EDSApplicationExamples:
    """EDS verilerini kullanan örnek uygulama kodları"""
    
    @staticmethod
    def driver_warning_system():
        """Sürücü uyarı sistemi örneği"""
        return """
        // React Native örnek kod
        import { useState, useEffect } from 'react';
        import Geolocation from '@react-native-geolocation-service';
        
        const DriverWarningApp = () => {
            const [currentLocation, setCurrentLocation] = useState(null);
            const [nearbyEDS, setNearbyEDS] = useState([]);
            
            useEffect(() => {
                // EDS verilerini yükle
                fetch('eds_export.json')
                    .then(response => response.json())
                    .then(data => checkNearbyEDS(data));
            }, [currentLocation]);
            
            const checkNearbyEDS = (edsData) => {
                if (!currentLocation) return;
                
                const nearby = edsData.filter(eds => {
                    const distance = calculateDistance(
                        currentLocation.latitude, 
                        currentLocation.longitude,
                        eds.latitude, 
                        eds.longitude
                    );
                    return distance < 1000; // 1km içinde
                });
                
                setNearbyEDS(nearby);
                
                if (nearby.length > 0) {
                    showWarning(nearby[0]);
                }
            };
        };
        """
    
    @staticmethod
    def route_optimizer():
        """Rota optimizasyon örneği"""
        return """
        // Python örnek kod
        import json
        from geopy.distance import geodesic
        
        class RouteOptimizer:
            def __init__(self, eds_data_file):
                with open(eds_data_file, 'r') as f:
                    self.eds_points = json.load(f)
            
            def find_safest_route(self, start_coords, end_coords):
                # A* algoritması ile EDS yoğunluğunu
                # dikkate alan en güvenli rotayı bul
                pass
            
            def calculate_route_risk_score(self, route_coords):
                risk_score = 0
                for coord in route_coords:
                    nearby_eds = self.get_eds_within_radius(coord, 500)
                    risk_score += len(nearby_eds) * 0.1
                return risk_score
        """

# Kullanım örneği
def main():
    collector = AlternativeEDSCollector()
    
    print("Alternatif kaynaklardan EDS verileri toplanıyor...")
    
    # Farklı kaynaklardan veri topla
    open_data = collector.collect_from_open_data_platforms()
    crowdsourced_data = collector.collect_from_crowdsourced_data()
    mobile_data = collector.collect_from_mobile_apps()
    
    # Verileri birleştir ve doğrula
    all_data = [open_data, crowdsourced_data, mobile_data]
    merged_data = collector.validate_and_merge_data(all_data)
    
    print(f"Toplam {len(merged_data)} EDS noktası bulundu")
    
    # Veritabanına kaydet
    collector.save_to_database(merged_data)
    
    # Uygulama geliştirme için export et
    collector.export_for_applications('all')
    
    print("Veriler başarıyla export edildi!")

if __name__ == "__main__":
    main()
