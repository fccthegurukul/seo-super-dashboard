# app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
import threading
import uuid
import json
import asyncio
from datetime import datetime, timedelta

# Logic scripts import
from analyzer_logic import run_full_scan, sanitize_url_for_filename, compare_scan_data
from scraper_logic import run_scrape, SCRAPED_DATA_DIR
from ai_content_generator import AIContentGenerator
from competitor_monitor import CompetitorMonitor
from automated_publisher import AutomatedPublisher

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-that-you-should-change'

# In-memory dictionary to track tasks
tasks_status = {}

# Initialize new components
ai_generator = AIContentGenerator()
competitor_monitor = CompetitorMonitor()
auto_publisher = AutomatedPublisher()

# Load existing data
competitor_monitor.load_competitors()
auto_publisher.load_sites_config()
auto_publisher.load_publishing_queue()

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

@app.route('/ai-generate', methods=['POST'])
def ai_generate_content():
    prompt = request.form.get('prompt')
    if not prompt:
        return "Error: Prompt is required.", 400
    
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {
        'type': 'AI Generation', 
        'status': 'running', 
        'progress': 0, 
        'message': 'Generating content with AI...'
    }
    
    def generate_content():
        try:
            tasks_status[task_id]['progress'] = 50
            result = ai_generator.generate_content_with_ai(prompt)
            
            if 'error' in result:
                tasks_status[task_id]['status'] = 'error'
                tasks_status[task_id]['message'] = result['error']
            else:
                tasks_status[task_id]['status'] = 'complete'
                tasks_status[task_id]['progress'] = 100
                tasks_status[task_id]['result'] = result
                tasks_status[task_id]['message'] = 'AI content generated successfully!'
        except Exception as e:
            tasks_status[task_id]['status'] = 'error'
            tasks_status[task_id]['message'] = str(e)
    
    thread = threading.Thread(target=generate_content)
    thread.start()
    return redirec
  t(url_for('dashboard'))

@app.route('/add-competitor', methods=['POST'])
def add_competitor():
    name = request.form.get('competitor_name')
    url = request.form.get('competitor_url')
    keywords = request.form.get('keywords', '').split(',')
    keywords = [k.strip() for k in keywords if k.strip()]
    
    if not name or not url:
        return "Error: Name and URL are required.", 400
    
    competitor_monitor.add_competitor(name, url, keywords)
    return redirect(url_for('competitors'))

@app.route('/competitors')
def competitors():
    competitor_monitor.load_competitors()
    return render_template('competitors.html', 
                         competitors=competitor_monitor.competitors,
                         opportunities=competitor_monitor.generate_opportunities_report())

@app.route('/start-competitor-monitoring', methods=['POST'])
def start_monitoring():
    competitor_monitor.start_monitoring()
    return jsonify({'status': 'Monitoring started successfully!'})

@app.route('/scan-competitors', methods=['POST'])
def manual_competitor_scan():
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {
        'type': 'Competitor Scan',
        'status': 'running',
        'progress': 0,
        'message': 'Scanning all competitors...'
    }
    
    def run_scan():
        try:
            asyncio.run(competitor_monitor.scan_all_competitors())
            tasks_status[task_id]['status'] = 'complete'
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['message'] = 'Competitor scan completed!'
        except Exception as e:
            tasks_status[task_id]['status'] = 'error'
            tasks_status[task_id]['message'] = str(e)
    
    thread = threading.Thread(target=run_scan)
    thread.start()
    return redirect(url_for('dashboard'))

@app.route('/add-wordpress-site', methods=['POST'])
def add_wordpress_site():
    name = request.form.get('site_name')
    url = request.form.get('site_url')
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not all([name, url, username, password]):
        return "Error: All fields are required.", 400
    
    result = auto_publisher.add_wordpress_site(name, url, username, password)
    return redirect(url_for('publishing'))

@app.route('/publishing')
def publishing():
    auto_publisher.load_sites_config()
    auto_publisher.load_publishing_queue()
    stats = auto_publisher.get_publishing_stats()
    
    return render_template('publishing.html',
                         sites=auto_publisher.wordpress_sites,
                         queue=auto_publisher.publishing_queue,
                         stats=stats)

@app.route('/auto-generate-and-publish', methods=['POST'])
def auto_generate_and_publish():
    scraped_task_id = request.form.get('scraped_task_id')
    target_sites = request.form.getlist('target_sites')
    
    if not scraped_task_id:
        return "Error: Scraped task ID required.", 400
    
    # Get scraped content
    scraped_task = tasks_status.get(scraped_task_id)
    if not scraped_task or scraped_task['status'] != 'complete':
        return "Error: Scraped content not found or incomplete.", 400
    
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {
        'type': 'Auto Generate & Publish',
        'status': 'running',
        'progress': 0,
        'message': 'Reading scraped content...'
    }
    
    def auto_process():
        try:
            # Read scraped content and AI prompt
            with open(scraped_task['scraped_file'], 'r', encoding='utf-8') as f:
                scraped_content = f.read()
            with open(scraped_task['prompt_file'], 'r', encoding='utf-8') as f:
                ai_prompt = f.read()
            
            tasks_status[task_id]['progress'] = 25
            tasks_status[task_id]['message'] = 'Generating AI content...'
            
            # Generate AI content
            ai_result = ai_generator.generate_content_with_ai(ai_prompt)
            
            if 'error' in ai_result:
                tasks_status[task_id]['status'] = 'error'
                tasks_status[task_id]['message'] = ai_result['error']
                return
            
            tasks_status[task_id]['progress'] = 75
            tasks_status[task_id]['message'] = 'Preparing for publishing...'
            
            # Create content for publishing
            content_data = auto_publisher.create_content_from_scrape(
                {'url': scraped_task['url']}, 
                ai_result
            )
            
            # Queue for publishing
            queue_item = auto_publisher.queue_content_for_publishing(
                content_data, 
                target_sites
            )
            
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['status'] = 'complete'
            tasks_status[task_id]['message'] = 'Content queued for publishing!'
            tasks_status[task_id]['queue_id'] = queue_item['id']
            
        except Exception as e:
            tasks_status[task_id]['status'] = 'error'
            tasks_status[task_id]['message'] = str(e)
    
    thread = threading.Thread(target=auto_process)
    thread.start()
    return redirect(url_for('dashboard'))

@app.route('/process-publishing-queue', methods=['POST'])
def process_queue():
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {
        'type': 'Publishing Queue',
        'status': 'running',
        'progress': 0,
        'message': 'Processing publishing queue...'
    }
    
    def process():
        try:
            auto_publisher.process_publishing_queue()
            tasks_status[task_id]['status'] = 'complete'
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['message'] = 'Publishing queue processed!'
        except Exception as e:
            tasks_status[task_id]['status'] = 'error'
            tasks_status[task_id]['message'] = str(e)
    
    thread = threading.Thread(target=process)
    thread.start()
    return redirect(url_for('dashboard'))

@app.route('/api/content-opportunities')
def get_content_opportunities():
    try:
        with open('monitoring_data/content_opportunities.json', 'r', encoding='utf-8') as f:
            opportunities = json.load(f)
        return jsonify(opportunities)
    except FileNotFoundError:
        return jsonify([])

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
    os.makedirs('monitoring_data', exist_ok=True)
    os.makedirs('publishing_data', exist_ok=True)
    app.run(debug=True, host='0.0.0.0')