#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EDS Veri Birleştirici ve Kalite Artırıcı - Advanced Data Merger
======================================================

Bu uygulama, farklı kaynaklardan toplanan EDS (Elektronik Denetleme Sistemi) 
verilerini birleştirerek tek bir kaliteli veri seti oluşturur.

Özellikler:
- Çoklu kaynak desteği (GeoJSON, JSON, CSV)
- Akıllı dublika tespit ve birleştirme
- Kalite skorlama ve filtreleme
- Coğrafi doğrulama (Türkiye sınırları)
- Standardizasyon ve normalizasyon
- Çoklu format export (GeoJSON, JSON, CSV, SQLite)

Author: AI Assistant
Version: 2.0.0
Date: 2025-06-10
"""

import json
import csv
import sqlite3
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
import argparse
import sys

# Gelişmiş matematik ve veri işleme için
import math
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from enum import Enum

# Optional: Gelişmiş özellikler için
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import geopy.distance
    HAS_GEOPY = True
except ImportError:
    HAS_GEOPY = False


class DataQuality(Enum):
    """Veri kalite seviyeleri"""
    EXCELLENT = "excellent"  # 0.9-1.0
    GOOD = "good"           # 0.7-0.89  
    FAIR = "fair"           # 0.5-0.69
    POOR = "poor"           # 0.3-0.49
    UNACCEPTABLE = "unacceptable"  # 0.0-0.29


class EDSType(Enum):
    """EDS kamera türleri"""
    OHITS = "OHITS"                    # Ortalama Hız İhlal Tespit Sistemi
    MOBILE = "MOBILE"                  # Mobil Radar
    REDLIGHT = "REDLIGHT"              # Kırmızı Işık Kamerası
    KIITS = "KIITS"                    # Kırmızı Işık İhlal Tespit Sistemi
    AVERAGE_SPEED = "AVERAGE_SPEED"    # Ortalama Hız Kamerası
    SECTION_CONTROL = "SECTION_CONTROL" # Kesit Kontrol
    WEIGHT_CONTROL = "WEIGHT_CONTROL"  # Ağırlık Kontrolü
    TUNNEL = "TUNNEL"                  # Tünel Kamerası
    UNKNOWN = "UNKNOWN"                # Bilinmeyen tip


@dataclass
class EDSPoint:
    """Standart EDS nokta veri yapısı"""
    id: str
    latitude: float
    longitude: float
    type: str
    city: Optional[str] = None
    district: Optional[str] = None
    road_name: Optional[str] = None
    speed_limit: Optional[int] = None
    direction: Optional[str] = None
    source: str = "unknown"
    confidence_score: float = 0.5
    timestamp: float = None
    osm_id: Optional[str] = None
    last_updated: Optional[str] = None
    status: str = "active"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()


class GeoValidator:
    """Coğrafi konum doğrulama sınıfı"""
    
    # Türkiye sınırları (yaklaşık)
    TURKEY_BOUNDS = {
        'min_lat': 35.8,
        'max_lat': 42.2,
        'min_lng': 25.7,
        'max_lng': 44.8
    }
    
    # Şehir merkezleri koordinatları
    CITY_CENTERS = {
        'Istanbul': (41.0082, 28.9784),
        'Ankara': (39.9334, 32.8597),
        'Izmir': (38.4237, 27.1428),
        'Bursa': (40.1826, 29.0669),
        'Antalya': (36.8841, 30.7056),
        'Adana': (37.0, 35.3213),
        'Konya': (37.8667, 32.4833),
        'Gaziantep': (37.0662, 37.3833),
        'Mersin': (36.8121, 34.6415),
        'Kayseri': (38.7312, 35.4787),
        'Eskisehir': (39.7767, 30.5206),
        'Diyarbakir': (37.9144, 40.2306),
        'Samsun': (41.2867, 36.33),
        'Denizli': (37.7765, 29.0864),
        'Sakarya': (40.6969, 30.4044),
        'Trabzon': (41.0015, 39.7178),
        'Van': (38.4891, 43.4089),
        'Erzurum': (39.9208, 41.2675)
    }
    
    @classmethod
    def is_in_turkey(cls, lat: float, lng: float) -> bool:
        """Koordinatın Türkiye sınırları içinde olup olmadığını kontrol eder"""
        return (cls.TURKEY_BOUNDS['min_lat'] <= lat <= cls.TURKEY_BOUNDS['max_lat'] and
                cls.TURKEY_BOUNDS['min_lng'] <= lng <= cls.TURKEY_BOUNDS['max_lng'])
    
    @classmethod
    def estimate_city(cls, lat: float, lng: float, threshold_km: float = 50) -> Optional[str]:
        """Koordinata en yakın şehri tahmin eder"""
        if not cls.is_in_turkey(lat, lng):
            return None
        
        min_distance = float('inf')
        closest_city = None
        
        for city, (city_lat, city_lng) in cls.CITY_CENTERS.items():
            if HAS_GEOPY:
                distance = geopy.distance.distance((lat, lng), (city_lat, city_lng)).kilometers
            else:
                # Haversine formülü
                distance = cls._haversine_distance(lat, lng, city_lat, city_lng)
            
            if distance < min_distance and distance <= threshold_km:
                min_distance = distance
                closest_city = city
        
        return closest_city if closest_city else "Diger"
    
    @staticmethod
    def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """İki koordinat arasındaki mesafeyi hesaplar (km)"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class QualityScorer:
    """Veri kalitesi puanlama sınıfı"""
    
    @staticmethod
    def calculate_confidence_score(data_point: Dict[str, Any]) -> float:
        """Veri noktası için güven skoru hesaplar"""
        score = 0.0
        
        # Kaynak güvenilirliği
        source = data_point.get('source', '').lower()
        if 'openstreetmap' in source or 'osm' in source:
            score += 0.3
        elif 'egm' in source or 'official' in source:
            score += 0.4
        elif 'community' in source or 'waze' in source:
            score += 0.2
        else:
            score += 0.1
        
        # Coğrafi doğruluk
        lat = data_point.get('latitude') or data_point.get('lat', 0)
        lng = data_point.get('longitude') or data_point.get('lng', 0)
        
        if GeoValidator.is_in_turkey(lat, lng):
            score += 0.2
        
        # Veri tamlığı
        completeness = 0
        required_fields = ['type', 'latitude', 'longitude']
        optional_fields = ['road_name', 'city', 'speed_limit', 'district']
        
        for field in required_fields:
            if field in data_point and data_point[field]:
                completeness += 0.1
        
        for field in optional_fields:
            if field in data_point and data_point[field]:
                completeness += 0.05
                
        score += min(completeness, 0.3)
        
        # OSM ID varsa bonus
        if data_point.get('osm_id'):
            score += 0.1
        
        # Mevcut confidence_score varsa kullan
        existing_score = data_point.get('confidence_score', 0)
        if existing_score > 0:
            score = (score + existing_score) / 2
        
        return min(score, 1.0)
    
    @staticmethod
    def get_quality_level(score: float) -> DataQuality:
        """Güven skoruna göre kalite seviyesi döner"""
        if score >= 0.9:
            return DataQuality.EXCELLENT
        elif score >= 0.7:
            return DataQuality.GOOD
        elif score >= 0.5:
            return DataQuality.FAIR
        elif score >= 0.3:
            return DataQuality.POOR
        else:
            return DataQuality.UNACCEPTABLE


class DataParser:
    """Farklı veri formatlarını parse eden sınıf"""
    
    @staticmethod
    def parse_geojson(file_path: str) -> List[Dict[str, Any]]:
        """GeoJSON dosyasını parse eder"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        points = []
        if data.get('type') == 'FeatureCollection':
            for feature in data.get('features', []):
                if feature.get('type') == 'Feature':
                    geometry = feature.get('geometry', {})
                    properties = feature.get('properties', {})
                    
                    if geometry.get('type') == 'Point':
                        coords = geometry.get('coordinates', [])
                        if len(coords) >= 2:
                            point = {
                                'longitude': coords[0],
                                'latitude': coords[1],
                                **properties
                            }
                            points.append(point)
        
        return points
    
    @staticmethod
    def parse_json(file_path: str) -> List[Dict[str, Any]]:
        """JSON dosyasını parse eder"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # GeoJSON olabilir
            if data.get('type') == 'FeatureCollection':
                return DataParser.parse_geojson(file_path)
            else:
                return [data]
        
        return []
    
    @staticmethod
    def parse_csv(file_path: str) -> List[Dict[str, Any]]:
        """CSV dosyasını parse eder"""
        points = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # String değerleri uygun tiplere çevir
                processed_row = {}
                for key, value in row.items():
                    key = key.strip()
                    if key in ['latitude', 'longitude', 'confidence_score', 'timestamp']:
                        try:
                            processed_row[key] = float(value)
                        except (ValueError, TypeError):
                            processed_row[key] = value
                    elif key in ['speed_limit']:
                        try:
                            processed_row[key] = int(value) if value else None
                        except (ValueError, TypeError):
                            processed_row[key] = None
                    else:
                        processed_row[key] = value
                
                points.append(processed_row)
        
        return points


class DuplicateDetector:
    """Dublika tespit ve birleştirme sınıfı"""
    
    def __init__(self, distance_threshold: float = 0.1):  # 100 metre
        self.distance_threshold = distance_threshold
    
    def find_duplicates(self, points: List[EDSPoint]) -> List[List[int]]:
        """Dublika grupları bulur"""
        duplicate_groups = []
        processed = set()
        
        for i, point1 in enumerate(points):
            if i in processed:
                continue
            
            group = [i]
            for j, point2 in enumerate(points[i+1:], i+1):
                if j in processed:
                    continue
                
                distance = GeoValidator._haversine_distance(
                    point1.latitude, point1.longitude,
                    point2.latitude, point2.longitude
                )
                
                if distance <= self.distance_threshold:
                    group.append(j)
                    processed.add(j)
            
            if len(group) > 1:
                duplicate_groups.append(group)
                processed.update(group)
            else:
                processed.add(i)
        
        return duplicate_groups
    
    def merge_duplicates(self, points: List[EDSPoint], duplicate_groups: List[List[int]]) -> List[EDSPoint]:
        """Dublikaları birleştirir"""
        merged_points = []
        all_duplicate_indices = set()
        
        for group in duplicate_groups:
            all_duplicate_indices.update(group)
            
            # En yüksek kaliteli noktayı seç
            best_point_idx = max(group, key=lambda i: points[i].confidence_score)
            best_point = points[best_point_idx]
            
            # Diğer noktalardan eksik bilgileri tamamla
            for idx in group:
                point = points[idx]
                if not best_point.road_name and point.road_name:
                    best_point.road_name = point.road_name
                if not best_point.speed_limit and point.speed_limit:
                    best_point.speed_limit = point.speed_limit
                if not best_point.district and point.district:
                    best_point.district = point.district
                if not best_point.osm_id and point.osm_id:
                    best_point.osm_id = point.osm_id
            
            # Güven skorunu artır (birden fazla kaynaktan gelmiş)
            best_point.confidence_score = min(best_point.confidence_score + 0.1 * len(group), 1.0)
            best_point.source += f" (merged from {len(group)} sources)"
            
            merged_points.append(best_point)
        
        # Dublika olmayan noktaları ekle
        for i, point in enumerate(points):
            if i not in all_duplicate_indices:
                merged_points.append(point)
        
        return merged_points


class AdvancedDataMerger:
    """Gelişmiş veri birleştirici ana sınıf"""
    
    def __init__(self, input_dir: str = "scraped-datas", output_dir: str = "merged-output"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Logging setup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'merger.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.parser = DataParser()
        self.duplicate_detector = DuplicateDetector()
        self.stats = defaultdict(int)
        
    def load_all_data(self) -> List[Dict[str, Any]]:
        """Tüm veri dosyalarını yükler"""
        all_data = []
        
        for file_path in self.input_dir.glob("*"):
            if file_path.is_file():
                self.logger.info(f"Loading file: {file_path.name}")
                
                try:
                    if file_path.suffix.lower() == '.geojson':
                        data = self.parser.parse_geojson(str(file_path))
                    elif file_path.suffix.lower() == '.json':
                        data = self.parser.parse_json(str(file_path))
                    elif file_path.suffix.lower() == '.csv':
                        data = self.parser.parse_csv(str(file_path))
                    else:
                        self.logger.warning(f"Unsupported file format: {file_path.suffix}")
                        continue
                    
                    self.logger.info(f"Loaded {len(data)} points from {file_path.name}")
                    self.stats[f'loaded_from_{file_path.name}'] = len(data)
                    all_data.extend(data)
                    
                except Exception as e:
                    self.logger.error(f"Error loading {file_path.name}: {e}")
        
        self.logger.info(f"Total raw data points loaded: {len(all_data)}")
        return all_data
    
    def normalize_data(self, raw_data: List[Dict[str, Any]]) -> List[EDSPoint]:
        """Ham veriyi normalize eder"""
        normalized_points = []
        
        for i, data_point in enumerate(raw_data):
            try:
                # Koordinat alanlarını standartlaştır
                lat = (data_point.get('latitude') or 
                      data_point.get('lat') or 
                      data_point.get('geometry', {}).get('coordinates', [None, None])[1])
                
                lng = (data_point.get('longitude') or 
                      data_point.get('lng') or 
                      data_point.get('lon') or
                      data_point.get('geometry', {}).get('coordinates', [None, None])[0])
                
                if not lat or not lng:
                    self.stats['missing_coordinates'] += 1
                    continue
                
                lat, lng = float(lat), float(lng)
                
                # Türkiye sınırları kontrolü
                if not GeoValidator.is_in_turkey(lat, lng):
                    self.stats['outside_turkey'] += 1
                    continue
                
                # EDS tip standardizasyonu
                eds_type = self.normalize_eds_type(data_point.get('type', 'UNKNOWN'))
                
                # Şehir tahmini
                city = (data_point.get('city') or 
                       GeoValidator.estimate_city(lat, lng))
                
                # Güven skoru hesaplama
                confidence_score = QualityScorer.calculate_confidence_score(data_point)
                
                # Kaliteli veri kontrolü
                quality = QualityScorer.get_quality_level(confidence_score)
                if quality == DataQuality.UNACCEPTABLE:
                    self.stats['unacceptable_quality'] += 1
                    continue
                
                # ID oluştur
                point_id = data_point.get('id') or f"eds_{i+1:06d}"
                
                # EDSPoint oluştur
                eds_point = EDSPoint(
                    id=point_id,
                    latitude=lat,
                    longitude=lng,
                    type=eds_type,
                    city=city,
                    district=data_point.get('district'),
                    road_name=data_point.get('road') or data_point.get('road_name'),
                    speed_limit=data_point.get('speed_limit'),
                    direction=data_point.get('direction'),
                    source=data_point.get('source', 'unknown'),
                    confidence_score=confidence_score,
                    timestamp=data_point.get('timestamp', time.time()),
                    osm_id=str(data_point.get('osm_id')) if data_point.get('osm_id') else None,
                    last_updated=data_point.get('last_updated') or datetime.now().isoformat(),
                    status=data_point.get('status', 'active')
                )
                
                normalized_points.append(eds_point)
                self.stats['normalized_points'] += 1
                
            except Exception as e:
                self.logger.warning(f"Error normalizing data point {i}: {e}")
                self.stats['normalization_errors'] += 1
        
        self.logger.info(f"Normalized {len(normalized_points)} points")
        return normalized_points
    
    def normalize_eds_type(self, type_str: str) -> str:
        """EDS tip adını standartlaştırır"""
        if not type_str:
            return EDSType.UNKNOWN.value
        
        type_str = type_str.upper().strip()
        
        # Mapping tablosu
        type_mapping = {
            'OHITS': EDSType.OHITS.value,
            'MOBILE': EDSType.MOBILE.value,
            'REDLIGHT': EDSType.REDLIGHT.value,
            'RED_LIGHT': EDSType.REDLIGHT.value,
            'KIITS': EDSType.KIITS.value,
            'AVERAGE_SPEED': EDSType.AVERAGE_SPEED.value,
            'SECTION_CONTROL': EDSType.SECTION_CONTROL.value,
            'WEIGHT_CONTROL': EDSType.WEIGHT_CONTROL.value,
            'TUNNEL': EDSType.TUNNEL.value,
            'EDS_POINT': EDSType.OHITS.value,  # Varsayılan olarak OHITS
        }
        
        return type_mapping.get(type_str, EDSType.UNKNOWN.value)
    
    def process_data(self) -> List[EDSPoint]:
        """Ana veri işleme pipeline'ı"""
        self.logger.info("Starting data processing pipeline...")
        
        # 1. Veri yükleme
        raw_data = self.load_all_data()
        
        # 2. Normalizasyon
        normalized_points = self.normalize_data(raw_data)
        
        # 3. Dublika tespiti ve birleştirme
        self.logger.info("Detecting and merging duplicates...")
        duplicate_groups = self.duplicate_detector.find_duplicates(normalized_points)
        self.stats['duplicate_groups'] = len(duplicate_groups)
        
        if duplicate_groups:
            merged_points = self.duplicate_detector.merge_duplicates(normalized_points, duplicate_groups)
            self.logger.info(f"Merged {len(normalized_points) - len(merged_points)} duplicate points")
        else:
            merged_points = normalized_points
        
        # 4. Kalite filtreleme
        self.logger.info("Applying quality filters...")
        high_quality_points = [
            point for point in merged_points 
            if point.confidence_score >= 0.3  # Minimum kalite eşiği
        ]
        
        self.stats['final_points'] = len(high_quality_points)
        self.stats['filtered_low_quality'] = len(merged_points) - len(high_quality_points)
        
        self.logger.info(f"Final dataset: {len(high_quality_points)} high-quality points")
        return high_quality_points
    
    def export_data(self, points: List[EDSPoint], base_filename: str = "eds_merged_data"):
        """Veriyi farklı formatlarda export eder"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = self.output_dir / f"{base_filename}_{timestamp}"
        
        # 1. GeoJSON Export
        geojson_data = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_points": len(points),
                "source": "Advanced EDS Data Merger v2.0",
                "quality_levels": self.get_quality_distribution(points)
            },
            "features": []
        }
        
        for point in points:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.longitude, point.latitude]
                },
                "properties": {
                    k: v for k, v in asdict(point).items() 
                    if k not in ['latitude', 'longitude']
                }
            }
            geojson_data["features"].append(feature)
        
        with open(f"{base_path}.geojson", 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        
        # 2. JSON Export
        json_data = [asdict(point) for point in points]
        with open(f"{base_path}.json", 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 3. CSV Export
        if points:
            fieldnames = list(asdict(points[0]).keys())
            with open(f"{base_path}.csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for point in points:
                    writer.writerow(asdict(point))
        
        # 4. SQLite Export
        self.export_to_sqlite(points, f"{base_path}.db")
        
        # 5. Statistics Export
        self.export_statistics(points, f"{base_path}_stats.json")
        
        self.logger.info(f"Data exported to: {base_path}.[geojson|json|csv|db]")
    
    def export_to_sqlite(self, points: List[EDSPoint], db_path: str):
        """SQLite veritabanına export eder"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tablo oluştur
        cursor.execute('''
            CREATE TABLE eds_points (
                id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                type TEXT NOT NULL,
                city TEXT,
                district TEXT,
                road_name TEXT,
                speed_limit INTEGER,
                direction TEXT,
                source TEXT,
                confidence_score REAL,
                timestamp REAL,
                osm_id TEXT,
                last_updated TEXT,
                status TEXT
            )
        ''')
        
        # Spatial index için ek tablo
        cursor.execute('''
            CREATE TABLE eds_spatial_index (
                id TEXT PRIMARY KEY,
                lat_grid INTEGER,
                lng_grid INTEGER,
                FOREIGN KEY (id) REFERENCES eds_points (id)
            )
        ''')
        
        # Veri ekle
        for point in points:
            data = asdict(point)
            placeholders = ', '.join(['?' for _ in data])
            cursor.execute(f'INSERT INTO eds_points VALUES ({placeholders})', list(data.values()))
            
            # Spatial index için grid hesapla (0.01 derece ~ 1km)
            lat_grid = int(point.latitude * 100)
            lng_grid = int(point.longitude * 100)
            cursor.execute('INSERT INTO eds_spatial_index VALUES (?, ?, ?)', 
                         (point.id, lat_grid, lng_grid))
        
        # Index'ler oluştur
        cursor.execute('CREATE INDEX idx_type ON eds_points (type)')
        cursor.execute('CREATE INDEX idx_city ON eds_points (city)')
        cursor.execute('CREATE INDEX idx_confidence ON eds_points (confidence_score)')
        cursor.execute('CREATE INDEX idx_spatial ON eds_spatial_index (lat_grid, lng_grid)')
        
        conn.commit()
        conn.close()
    
    def get_quality_distribution(self, points: List[EDSPoint]) -> Dict[str, int]:
        """Kalite dağılımını hesaplar"""
        distribution = defaultdict(int)
        for point in points:
            quality = QualityScorer.get_quality_level(point.confidence_score)
            distribution[quality.value] += 1
        return dict(distribution)
    
    def export_statistics(self, points: List[EDSPoint], stats_path: str):
        """İstatistikleri export eder"""
        stats = {
            "generation_info": {
                "timestamp": datetime.now().isoformat(),
                "total_points": len(points),
                "processing_stats": dict(self.stats)
            },
            "quality_distribution": self.get_quality_distribution(points),
            "type_distribution": dict(Counter(point.type for point in points)),
            "city_distribution": dict(Counter(point.city for point in points if point.city)),
            "source_distribution": dict(Counter(point.source for point in points)),
            "geographic_coverage": {
                "min_latitude": min(point.latitude for point in points),
                "max_latitude": max(point.latitude for point in points),
                "min_longitude": min(point.longitude for point in points),
                "max_longitude": max(point.longitude for point in points)
            },
            "confidence_stats": {
                "average": sum(point.confidence_score for point in points) / len(points),
                "min": min(point.confidence_score for point in points),
                "max": max(point.confidence_score for point in points)
            }
        }
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)


def main():
    """Ana uygulama fonksiyonu"""
    parser = argparse.ArgumentParser(description='Advanced EDS Data Merger')
    parser.add_argument('--input-dir', default='scraped-datas', 
                       help='Input directory containing scraped data files')
    parser.add_argument('--output-dir', default='merged-output',
                       help='Output directory for merged data')
    parser.add_argument('--min-quality', type=float, default=0.3,
                       help='Minimum quality threshold (0.0-1.0)')
    parser.add_argument('--duplicate-threshold', type=float, default=0.1,
                       help='Duplicate detection distance threshold (km)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Merger oluştur ve çalıştır
    merger = AdvancedDataMerger(args.input_dir, args.output_dir)
    merger.duplicate_detector.distance_threshold = args.duplicate_threshold
    
    try:
        # Veri işleme
        processed_points = merger.process_data()
        
        # Kalite filtreleme
        high_quality_points = [
            point for point in processed_points 
            if point.confidence_score >= args.min_quality
        ]
        
        print(f"\n🎯 Processing Complete!")
        print(f"📊 Final Dataset: {len(high_quality_points)} high-quality EDS points")
        print(f"📍 Geographic Coverage: Turkey")
        print(f"⭐ Average Quality Score: {sum(p.confidence_score for p in high_quality_points) / len(high_quality_points):.3f}")
        
        # Export
        merger.export_data(high_quality_points)
        
        print(f"✅ All data exported to: {merger.output_dir}")
        print(f"📁 Available formats: GeoJSON, JSON, CSV, SQLite")
        
    except Exception as e:
        merger.logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
