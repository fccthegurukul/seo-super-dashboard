# analyzer_logic.py

import os
import json
import asyncio
import aiohttp
import re
import hashlib
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# --- Configuration and Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SCAN_DATA_DIR = "scans"
MAX_CONCURRENT_REQUESTS = 50

# --- Helper and Logic Functions ---
def sanitize_url_for_filename(url):
    return re.sub(r'https?://', '', url).replace('/', '_').replace('.', '-')

def get_base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

async def fetch_and_parse_sitemap_recursively(session, sitemap_url, processed_sitemaps):
    if sitemap_url in processed_sitemaps:
        return []
    processed_sitemaps.add(sitemap_url)
    
    urls = []
    try:
        async with session.get(sitemap_url, timeout=20) as response:
            if response.status != 200:
                logging.error(f"Sitemap {sitemap_url} returned status {response.status}.")
                return []
            
            content = await response.text()
            content = re.sub(' xmlns="[^"]+"', '', content, count=1)
            root = ET.fromstring(content)
            
            if root.tag.endswith('sitemapindex'):
                child_sitemap_urls = [s.find('loc').text for s in root.findall('sitemap') if s.find('loc') is not None]
                tasks = [fetch_and_parse_sitemap_recursively(session, child_url, processed_sitemaps) for child_url in child_sitemap_urls]
                results = await asyncio.gather(*tasks)
                for result_list in results:
                    urls.extend(result_list)
            
            elif root.tag.endswith('urlset'):
                for url_node in root.findall('url'):
                    loc_node = url_node.find('loc')
                    if loc_node is not None and loc_node.text:
                        loc = loc_node.text
                        lastmod_node = url_node.find('lastmod')
                        lastmod = lastmod_node.text if lastmod_node is not None else 'N/A'
                        urls.append({'url': loc, 'last_modified': lastmod})
    except Exception as e:
        logging.error(f"Error fetching or parsing sitemap {sitemap_url}: {e}")
    return urls

async def get_all_sitemap_urls(session, base_url):
    sitemap_locations = []
    try:
        robots_url = urljoin(base_url, '/robots.txt')
        async with session.get(robots_url, timeout=10) as response:
            text = await response.text()
            sitemap_locations = re.findall(r'Sitemap:\s*(.*)', text, re.IGNORECASE)
    except Exception as e:
        logging.warning(f"Could not find or parse robots.txt: {e}")

    if not sitemap_locations:
        sitemap_locations.append(urljoin(base_url, '/sitemap.xml'))
        sitemap_locations.append(urljoin(base_url, '/sitemap_index.xml'))
    
    processed_sitemaps = set()
    tasks = [fetch_and_parse_sitemap_recursively(session, url.strip(), processed_sitemaps) for url in sitemap_locations]
    results = await asyncio.gather(*tasks)
    
    all_urls = [item for sublist in results for item in sublist]
    unique_urls = list({item['url']: item for item in all_urls}.values())
    return unique_urls

async def check_url_health(session, url_data, semaphore):
    url = url_data['url']
    async with semaphore:
        try:
            async with session.get(url, timeout=15, allow_redirects=True) as response:
                status = response.status
                final_url = str(response.url)
                
                content_hash = None
                if status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    title = soup.title.string.strip() if soup.title else ''
                    desc_tag = soup.find('meta', attrs={'name': 'description'})
                    content = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''
                    h1_tag = soup.h1
                    h1 = h1_tag.get_text(strip=True) if h1_tag else ''
                    key_content = f"{title}{h1}{content}".encode('utf-8')
                    content_hash = hashlib.md5(key_content).hexdigest()
                
                return {**url_data, "http_status": status, "content_hash": content_hash, "final_url": final_url, "error": None}
        except Exception as e:
            return {**url_data, "http_status": "Error", "content_hash": None, "final_url": url, "error": str(e)}

def categorize_url(url):
    path = urlparse(url).path.lower()
    if any(s in path for s in ['/blog/', '/post/', '/article/', '/news/']): return 'Post/Article'
    if any(s in path for s in ['/web-stories/', '/web-story/']): return 'Web Story'
    if any(s in path for s in ['/product/', '/shop/']): return 'Product'
    if any(s in path for s in ['/category/', '/collection/']): return 'Category Page'
    if path == '/' or not path: return 'Homepage'
    return 'Other Page'
    
def compare_scan_data(old_data, new_data):
    old_map = {item['url']: item for item in old_data}
    new_map = {item['url']: item for item in new_data}
    old_urls = set(old_map.keys())
    new_urls = set(new_map.keys())
    added = [new_map[url] for url in (new_urls - old_urls)]
    removed = [old_map[url] for url in (old_urls - new_urls)]
    updated = []
    for url in (old_urls & new_urls):
        item_old = old_map[url]
        item_new = new_map[url]
        changes = {}
        if item_old.get('last_modified') != item_new.get('last_modified'):
            changes['last_modified'] = (item_old.get('last_modified'), item_new.get('last_modified'))
        if item_old.get('http_status') != item_new.get('http_status'):
            changes['http_status'] = (item_old.get('http_status'), item_new.get('http_status'))
        if item_old.get('content_hash') != item_new.get('content_hash') and item_new.get('content_hash') is not None:
             changes['content_hash'] = ('Content Changed', 'Content Changed')
        if changes:
            updated.append({'url': url, 'changes': changes})
    return {'added': added, 'removed': removed, 'updated': updated}

async def _async_core_scanner(base_url, scan_id, status_dict):
    try:
        async with aiohttp.ClientSession() as session:
            status_dict[scan_id]['status'] = 'running'
            status_dict[scan_id]['progress'] = 5
            status_dict[scan_id]['message'] = 'Fetching sitemaps...'
            
            sitemap_urls = await get_all_sitemap_urls(session, base_url)
            
            if not sitemap_urls:
                status_dict[scan_id] = {**status_dict[scan_id], 'status': 'error', 'message': 'No URLs found or sitemap not accessible.'}
                return

            total_urls = len(sitemap_urls)
            final_results = []
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
            tasks = [check_url_health(session, url_data, semaphore) for url_data in sitemap_urls]
            
            for i, future in enumerate(asyncio.as_completed(tasks)):
                result = await future
                result['category'] = categorize_url(result.get('final_url', result['url']))
                final_results.append(result)
                progress = int(((i + 1) / total_urls) * 100)
                status_dict[scan_id]['progress'] = progress
                status_dict[scan_id]['message'] = f'Checking {i+1}/{total_urls}'
        
        sanitized_url = sanitize_url_for_filename(base_url)
        site_scan_dir = os.path.join(SCAN_DATA_DIR, sanitized_url)
        os.makedirs(site_scan_dir, exist_ok=True)
        filename = os.path.join(site_scan_dir, f"{scan_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=4)
        
        status_dict[scan_id]['status'] = 'complete'
        status_dict[scan_id]['message'] = f'Scan complete! Results saved.'
        status_dict[scan_id]['file'] = filename

    except Exception as e:
        logging.error(f"Error during scan for {base_url}: {e}")
        status_dict[scan_id]['status'] = 'error'
        status_dict[scan_id]['message'] = str(e)

def run_full_scan(base_url, scan_id, status_dict):
    try:
        # On Windows, you might need a specific event loop policy for asyncio in threads
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        # Other OS's don't have this
        pass
    asyncio.run(_async_core_scanner(base_url, scan_id, status_dict))