#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EDS Data Merger - Web Backend
============================

Flask web server for EDS data merger web interface.
Handles file uploads, processing, and downloads.
"""

import os
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import sys
import logging

# Import our data merger
sys.path.append(str(Path(__file__).parent))
from advanced_data_merger import AdvancedDataMerger

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store processing results temporarily
processing_results = {}

ALLOWED_EXTENSIONS = {'json', 'geojson', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Ana sayfa"""
    with open('web_interface.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/upload', methods=['POST'])
def upload_files():
    """Dosya yükleme endpoint'i"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to prevent conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"
                filepath = upload_dir / filename
                file.save(str(filepath))
                
                uploaded_files.append({
                    'name': file.filename,
                    'path': str(filepath),
                    'size': filepath.stat().st_size
                })
        
        if not uploaded_files:
            return jsonify({'error': 'No valid files uploaded'}), 400
        
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'message': f'{len(uploaded_files)} file(s) uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_data():
    """Veri işleme endpoint'i"""
    try:
        data = request.get_json()
        
        # Parameters
        files = data.get('files', [])
        settings = data.get('settings', {})
        
        if not files:
            return jsonify({'error': 'No files to process'}), 400
        
        # Create temporary input directory
        temp_input_dir = Path(tempfile.mkdtemp())
        
        # Copy uploaded files to temp directory
        for file_info in files:
            src_path = Path(file_info['path'])
            if src_path.exists():
                dst_path = temp_input_dir / file_info['name']
                dst_path.write_bytes(src_path.read_bytes())
        
        # Create output directory
        output_dir = Path(tempfile.mkdtemp())
        
        # Initialize merger
        merger = AdvancedDataMerger(str(temp_input_dir), str(output_dir))
        merger.duplicate_detector.distance_threshold = settings.get('duplicateDistance', 0.1)
        
        # Process data
        logger.info("Starting data processing...")
        processed_points = merger.process_data()
        
        # Apply quality filter
        min_quality = settings.get('qualityThreshold', 0.3)
        high_quality_points = [
            point for point in processed_points 
            if point.confidence_score >= min_quality
        ]
        
        # Export data
        output_name = settings.get('outputName', 'eds_merged_data')
        merger.export_data(high_quality_points, output_name)
        
        # Prepare results
        from collections import Counter
        results = {
            'totalPoints': len(high_quality_points),
            'qualityScore': sum(p.confidence_score for p in high_quality_points) / len(high_quality_points) if high_quality_points else 0,
            'duplicatesRemoved': merger.stats.get('duplicate_groups', 0),
            'typeDistribution': dict(Counter(p.type for p in high_quality_points)),
            'cityDistribution': dict(Counter(p.city for p in high_quality_points if p.city)),
            'processingStats': dict(merger.stats),
            'outputDir': str(output_dir)
        }
        
        # Store results for download
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        processing_results[session_id] = {
            'results': results,
            'output_dir': output_dir,
            'created_at': datetime.now()
        }
        
        # Clean up input directory
        import shutil
        shutil.rmtree(temp_input_dir, ignore_errors=True)
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<session_id>/<format>')
def download_file(session_id, format):
    """Dosya indirme endpoint'i"""
    try:
        if session_id not in processing_results:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = processing_results[session_id]
        output_dir = Path(session_data['output_dir'])
        
        if format == 'all':
            # Create ZIP file with all outputs
            zip_path = output_dir / 'eds_merged_data_all.zip'
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in output_dir.glob('eds_merged_data_*'):
                    if file_path.suffix != '.zip':
                        zipf.write(file_path, file_path.name)
            
            return send_file(str(zip_path), as_attachment=True, 
                           download_name='eds_merged_data_all.zip')
        
        else:
            # Find specific format file
            pattern = f'eds_merged_data_*.{format}'
            files = list(output_dir.glob(pattern))
            
            if not files:
                return jsonify({'error': f'File not found for format: {format}'}), 404
            
            file_path = files[0]
            return send_file(str(file_path), as_attachment=True, 
                           download_name=file_path.name)
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<session_id>')
def get_status(session_id):
    """İşlem durumu sorgulama"""
    if session_id in processing_results:
        return jsonify({
            'status': 'completed',
            'results': processing_results[session_id]['results']
        })
    else:
        return jsonify({'status': 'not_found'}), 404

@app.route('/api/info')
def api_info():
    """API bilgileri"""
    return jsonify({
        'name': 'EDS Data Merger API',
        'version': '2.0.0',
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size': '50MB',
        'features': [
            'Multi-format support',
            'Duplicate detection',
            'Quality scoring',
            'Geographic validation',
            'Multiple export formats'
        ]
    })

# Clean up old results periodically
@app.before_request
def cleanup_old_results():
    """Eski sonuçları temizle (1 saatlik)"""
    import time
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, data in processing_results.items():
        if (current_time - data['created_at']).seconds > 3600:  # 1 hour
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        session_data = processing_results.pop(session_id)
        # Clean up files
        import shutil
        try:
            shutil.rmtree(session_data['output_dir'], ignore_errors=True)
        except:
            pass

if __name__ == '__main__':
    print("🚀 EDS Data Merger Web Server starting...")
    print("📍 Local URL: http://localhost:5000")
    print("🔧 API Docs: http://localhost:5000/api/info")
    print("📁 Upload folder:", app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True, host='0.0.0.0', port=5000)
