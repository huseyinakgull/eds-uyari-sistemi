#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EDS Veri Entegrasyonu - Integration Script
==========================================

Bu script, birleştirilmiş EDS verilerini ana uygulamaya entegre eder.
"""

import json
import shutil
from pathlib import Path
import sys

def find_latest_merged_data():
    """En son birleştirilmiş veriyi bulur"""
    tools_dir = Path(__file__).parent
    output_dirs = [
        tools_dir / "merged-output",
        tools_dir / "../merged-output",
        Path("merged-output")
    ]
    
    latest_file = None
    latest_time = 0
    
    for output_dir in output_dirs:
        if output_dir.exists():
            for geojson_file in output_dir.glob("eds_merged_data_*.geojson"):
                mtime = geojson_file.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = geojson_file
    
    return latest_file

def update_main_app(geojson_file):
    """Ana uygulamayı günceller"""
    # Hedef dizinler
    main_data_dir = Path(__file__).parent.parent / "data"
    main_data_dir.mkdir(exist_ok=True)
    
    # GeoJSON dosyasını kopyala
    target_file = main_data_dir / "eds-locations.geojson"
    shutil.copy2(geojson_file, target_file)
    
    # Veri sayısını kontrol et
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    point_count = len(data.get('features', []))
    
    print(f"✅ {point_count} EDS noktası ana uygulamaya entegre edildi")
    print(f"📁 Hedef dosya: {target_file}")
    
    return point_count, target_file

def update_index_html(point_count):
    """Index.html'i gerçek veri ile günceller"""
    index_file = Path(__file__).parent.parent / "index.html"
    
    if not index_file.exists():
        print(f"⚠️ Index.html bulunamadı: {index_file}")
        return False
    
    # Index.html'i oku
    content = index_file.read_text(encoding='utf-8')
    
    # Test verilerini gerçek veri yükleme ile değiştir
    old_fallback = '''console.warn('⚠️ GeoJSON yüklenemedi, test verileri kullanılıyor');
                // Fallback test data
                edsLocations = ['''
    
    new_code = f'''console.log('✅ EDS verileri yüklendi:', edsLocations.length, 'kamera');
                
                // Veri sayısını güncelle
                document.getElementById('edsCount').textContent = edsLocations.length + ' Kamera';'''
    
    # Test veri bloğunu kaldır ve gerçek veri yükleme ekle
    if 'Fallback test data' in content:
        # Test veri bloğunu bul ve kaldır
        start = content.find('// Fallback test data')
        end = content.find('];', start) + 2
        if start != -1 and end != -1:
            # Test veriyi kaldır
            before = content[:start]
            after = content[end:]
            content = before + new_code + after
            
            # Dosyayı güncelle
            index_file.write_text(content, encoding='utf-8')
            print(f"✅ Index.html güncellendi - {point_count} kamera ile")
            return True
    
    print("⚠️ Index.html güncelleme gerekli değil")
    return True

def main():
    """Ana entegrasyon fonksiyonu"""
    print("🔗 EDS Veri Entegrasyonu Başlatılıyor...")
    print("=" * 50)
    
    # En son birleştirilmiş veriyi bul
    latest_file = find_latest_merged_data()
    
    if not latest_file:
        print("❌ Birleştirilmiş EDS verisi bulunamadı!")
        print("💡 Önce şu adımları yapın:")
        print("   1. cd tools/")
        print("   2. python run_merger.py")
        print("   3. Bu script'i tekrar çalıştırın")
        return False
    
    print(f"📄 Bulunan veri dosyası: {latest_file.name}")
    
    # Ana uygulamaya entegre et
    point_count, target_file = update_main_app(latest_file)
    
    # Index.html'i güncelle
    update_index_html(point_count)
    
    print("\n🎉 ENTEGRASYON TAMAMLANDI!")
    print(f"📊 Toplam EDS noktası: {point_count:,}")
    print(f"📁 Veri dosyası: {target_file}")
    print(f"🌐 Ana uygulama hazır: ../index.html")
    
    print("\n🚀 Test etmek için:")
    print("   1. Ana dizinde: open index.html")
    print("   2. GPS tracking'i başlatın")
    print("   3. Uyarıları test edin")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ İşlem iptal edildi")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        sys.exit(1)
