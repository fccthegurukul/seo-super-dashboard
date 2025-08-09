# app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
import threading
import uuid
import json

# Logic scripts import
from analyzer_logic import run_full_scan, sanitize_url_for_filename, compare_scan_data
from scraper_logic import run_scrape, SCRAPED_DATA_DIR

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-that-you-should-change'

# In-memory dictionary to track tasks
tasks_status = {}

@app.route('/')
def dashboard():
    sorted_tasks = dict(reversed(list(tasks_status.items())))
    scanned_sites = [d for d in os.listdir('scans') if os.path.isdir(os.path.join('scans', d))]
    return render_template('dashboard.html', tasks=sorted_tasks, scanned_sites=scanned_sites)

@app.route('/start-scan', methods=['POST'])
def start_scan_route():
    url = request.form.get('url')
    if not url: return "Error: URL is required.", 400
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'type': 'Sitemap Scan', 'status': 'queued', 'progress': 0, 'url': url, 'message': 'Waiting to start...'}
    thread = threading.Thread(target=run_full_scan, args=(url, task_id, tasks_status))
    thread.start()
    return redirect(url_for('dashboard'))

@app.route('/start-scrape', methods=['POST'])
def start_scrape_route():
    article_url = request.form.get('article_url')
    publisher_name = request.form.get('publisher_name')
    if not article_url or not publisher_name: return "Error: All fields are required.", 400
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'type': 'Content Scrape', 'status': 'queued', 'progress': 0, 'url': article_url, 'message': 'Waiting to start...'}
    thread = threading.Thread(target=run_scrape, args=(article_url, publisher_name, task_id, tasks_status))
    thread.start()
    return redirect(url_for('dashboard'))

@app.route('/scraped-media/<path:filename>')
def scraped_media(filename):
    base_dir = os.path.abspath(SCRAPED_DATA_DIR)
    return send_from_directory(base_dir, filename)

@app.route('/site/<site_name>')
def site_details(site_name):
    site_dir = os.path.join('scans', site_name)
    if not os.path.exists(site_dir): return "Site not found", 404
    scan_files = sorted([f for f in os.listdir(site_dir) if f.endswith('.json')], reverse=True)
    latest_scan_data = []
    if scan_files:
        with open(os.path.join(site_dir, scan_files[0]), 'r', encoding='utf-8') as f:
            latest_scan_data = json.load(f)
    return render_template('site_details.html', site_name=site_name, scan_files=scan_files, data=latest_scan_data)
    
@app.route('/api/compare', methods=['POST'])
def compare_scans_api():
    data = request.json
    site_dir = os.path.join('scans', data.get('site_name'))
    with open(os.path.join(site_dir, data.get('file_a')), 'r') as f1, \
         open(os.path.join(site_dir, data.get('file_b')), 'r') as f2:
        data_a, data_b = json.load(f1), json.load(f2)
    return jsonify(compare_scan_data(data_a, data_b))

@app.route('/task-status/<task_id>')
def get_task_status(task_id):
    return jsonify(tasks_status.get(task_id, {'status': 'not_found'}))

@app.route('/results/<task_id>')
def view_results(task_id):
    result_info = tasks_status.get(task_id)
    if not result_info or result_info.get('status') != 'complete': return "Task not found or not complete.", 404

    if result_info['type'] == 'Sitemap Scan':
        return redirect(url_for('site_details', site_name=sanitize_url_for_filename(result_info['url'])))
    
    elif result_info['type'] == 'Content Scrape':
        try:
            with open(result_info['scraped_file'], 'r', encoding='utf-8') as f: scraped_content = f.read()
            with open(result_info['prompt_file'], 'r', encoding='utf-8') as f: ai_prompt = f.read()
            
            image_folder_abs_path = result_info.get('image_folder')
            web_image_paths = []
            if image_folder_abs_path and os.path.exists(image_folder_abs_path):
                base_dir_abs_path = os.path.abspath(SCRAPED_DATA_DIR)
                relative_folder_path = os.path.relpath(image_folder_abs_path, base_dir_abs_path)
                for img_name in sorted(os.listdir(image_folder_abs_path)):
                    final_web_path = os.path.join(relative_folder_path, img_name).replace('\\', '/')
                    web_image_paths.append(final_web_path)

            return render_template('scraper_results.html',
                                   scraped_content=scraped_content, ai_prompt=ai_prompt,
                                   web_image_paths=web_image_paths, url=result_info['url'])
        except Exception as e:
            print(f"ERROR reading result files for task {task_id}: {e}")
            return f"Could not read result files: {e}", 500
    
    return "Unknown result type", 400

if __name__ == '__main__':
    os.makedirs('scans', exist_ok=True)
    os.makedirs(SCRAPED_DATA_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')