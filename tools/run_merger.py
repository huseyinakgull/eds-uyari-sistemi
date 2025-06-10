#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EDS Data Merger - Basit Çalıştırıcı
===================================

Bu script, EDS verilerini birleştirmek için basit bir arayüz sağlar.
Sadece çalıştırın ve adımları takip edin!

Usage: python run_merger.py
"""

import os
import sys
from pathlib import Path

# Ana merger'ı import et
sys.path.append(str(Path(__file__).parent))
from advanced_data_merger import AdvancedDataMerger

def print_banner():
    """Güzel bir banner yazdır"""
    print("="*60)
    print("🚨 EDS VERİ BİRLEŞTİRİCİ - Advanced Data Merger")
    print("="*60)
    print("📊 Tüm EDS verilerinizi tek bir kaliteli veri setinde birleştirin!")
    print()

def check_input_directory():
    """Input dizinini kontrol et"""
    scraped_dir = Path("../scrapers/scraped-datas")
    
    if not scraped_dir.exists():
        print("❌ scraped-datas dizini bulunamadı!")
        print(f"   Beklenen konum: {scraped_dir.absolute()}")
        return None
    
    # Dosyaları listele
    files = list(scraped_dir.glob("*"))
    data_files = [f for f in files if f.suffix.lower() in ['.json', '.geojson', '.csv']]
    
    if not data_files:
        print("❌ scraped-datas dizininde veri dosyası bulunamadı!")
        print("   Desteklenen formatlar: .json, .geojson, .csv")
        return None
    
    print(f"✅ {len(data_files)} veri dosyası bulundu:")
    for file in data_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"   📄 {file.name} ({size_mb:.1f}MB)")
    
    return str(scraped_dir)

def get_user_preferences():
    """Kullanıcı tercihlerini al"""
    print("\n🔧 AYARLAR:")
    print("-" * 20)
    
    # Kalite eşiği
    while True:
        try:
            quality = input("📊 Minimum kalite eşiği (0.1-1.0) [varsayılan: 0.3]: ").strip()
            if not quality:
                quality = 0.3
                break
            quality = float(quality)
            if 0.1 <= quality <= 1.0:
                break
            else:
                print("   ⚠️  Lütfen 0.1-1.0 arasında bir değer girin")
        except ValueError:
            print("   ⚠️  Lütfen geçerli bir sayı girin")
    
    # Dublika mesafesi
    while True:
        try:
            distance = input("📍 Dublika tespit mesafesi (km) [varsayılan: 0.1]: ").strip()
            if not distance:
                distance = 0.1
                break
            distance = float(distance)
            if 0.01 <= distance <= 5.0:
                break
            else:
                print("   ⚠️  Lütfen 0.01-5.0 arasında bir değer girin")
        except ValueError:
            print("   ⚠️  Lütfen geçerli bir sayı girin")
    
    # Output dizini
    output_dir = input("📂 Çıktı dizini [varsayılan: merged-output]: ").strip()
    if not output_dir:
        output_dir = "merged-output"
    
    return {
        'min_quality': quality,
        'duplicate_threshold': distance,
        'output_dir': output_dir
    }

def run_merger_with_progress(input_dir, preferences):
    """Merger'ı progress ile çalıştır"""
    print("\n🚀 VERİ BİRLEŞTİRME BAŞLATILIYOR...")
    print("=" * 40)
    
    try:
        # Merger oluştur
        merger = AdvancedDataMerger(input_dir, preferences['output_dir'])
        merger.duplicate_detector.distance_threshold = preferences['duplicate_threshold']
        
        print("📥 1/4 - Veri dosyaları yükleniyor...")
        raw_data = merger.load_all_data()
        
        print("🔧 2/4 - Veriler normalize ediliyor...")
        normalized_points = merger.normalize_data(raw_data)
        
        print("🔍 3/4 - Dublikalar tespit ediliyor ve birleştiriliyor...")
        duplicate_groups = merger.duplicate_detector.find_duplicates(normalized_points)
        
        if duplicate_groups:
            merged_points = merger.duplicate_detector.merge_duplicates(normalized_points, duplicate_groups)
            print(f"   ✅ {len(duplicate_groups)} dublika grubu birleştirildi")
        else:
            merged_points = normalized_points
            print("   ✅ Dublika bulunamadı")
        
        # Kalite filtreleme
        high_quality_points = [
            point for point in merged_points 
            if point.confidence_score >= preferences['min_quality']
        ]
        
        print("💾 4/4 - Sonuçlar export ediliyor...")
        merger.export_data(high_quality_points)
        
        return high_quality_points, merger.stats
        
    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
        return None, None

def show_results(points, stats, output_dir):
    """Sonuçları göster"""
    if not points:
        print("\n❌ İşlem başarısız!")
        return
    
    print("\n🎉 İŞLEM TAMAMLANDI!")
    print("=" * 40)
    print(f"📊 Toplam kaliteli nokta: {len(points)}")
    print(f"🎯 Ortalama kalite skoru: {sum(p.confidence_score for p in points) / len(points):.3f}")
    print(f"📂 Çıktı dizini: {output_dir}")
    
    # Tip dağılımı
    from collections import Counter
    type_dist = Counter(p.type for p in points)
    print(f"\n📈 Kamera Tip Dağılımı:")
    for camera_type, count in type_dist.most_common():
        print(f"   {camera_type}: {count} adet")
    
    # Şehir dağılımı (en çok 5 şehir)
    city_dist = Counter(p.city for p in points if p.city)
    print(f"\n🏙️  En Çok Kameranın Olduğu Şehirler:")
    for city, count in city_dist.most_common(5):
        print(f"   {city}: {count} adet")
    
    print(f"\n📁 Oluşturulan dosyalar:")
    output_path = Path(output_dir)
    for file in output_path.glob("eds_merged_data_*"):
        print(f"   📄 {file.name}")
    
    print(f"\n✅ Artık bu verileri EDS uyarı sisteminizde kullanabilirsiniz!")

def main():
    """Ana fonksiyon"""
    print_banner()
    
    # Input dizini kontrol
    input_dir = check_input_directory()
    if not input_dir:
        print("\n💡 ÖNERİ:")
        print("   1. Önce scrapers/scraped-datas dizininizde veri olduğundan emin olun")
        print("   2. python egm_eds_parser.py ile veri toplayın")
        print("   3. Bu script'i tekrar çalıştırın")
        return
    
    # Kullanıcı tercihleri
    preferences = get_user_preferences()
    
    # Onay
    print(f"\n📋 ÖZET:")
    print(f"   📥 Kaynak: {input_dir}")
    print(f"   📊 Min. kalite: {preferences['min_quality']}")
    print(f"   📍 Dublika mesafesi: {preferences['duplicate_threshold']} km")
    print(f"   📂 Çıktı: {preferences['output_dir']}")
    
    confirm = input(f"\n❓ İşleme başlansın mı? (e/h) [e]: ").strip().lower()
    if confirm and confirm not in ['e', 'evet', 'y', 'yes']:
        print("❌ İşlem iptal edildi.")
        return
    
    # İşlemi çalıştır
    points, stats = run_merger_with_progress(input_dir, preferences)
    
    # Sonuçları göster
    show_results(points, stats, preferences['output_dir'])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ İşlem kullanıcı tarafından iptal edildi.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        print("📧 Bu hatayı rapor edebilirsiniz.")
