# automated_publisher.py

import os
import json
import requests
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost, GetPosts
from wordpress_xmlrpc.methods.media import UploadFile
import base64

class AutomatedPublisher:
    def __init__(self):
        self.wordpress_sites = []
        self.publishing_queue = []
        
    def add_wordpress_site(self, name, url, username, password):
        """WordPress site add karta hai"""
        site_config = {
            'name': name,
            'url': url,
            'username': username,
            'password': password,
            'xmlrpc_url': f"{url.rstrip('/')}/xmlrpc.php",
            'added_date': datetime.now().isoformat()
        }
        
        # Test connection
        try:
            client = Client(site_config['xmlrpc_url'], username, password)
            # Test with a simple call
            posts = client.call(GetPosts({'number': 1}))
            site_config['status'] = 'connected'
            site_config['last_test'] = datetime.now().isoformat()
        except Exception as e:
            site_config['status'] = 'error'
            site_config['error'] = str(e)
        
        self.wordpress_sites.append(site_config)
        self.save_sites_config()
        return site_config
    
    def save_sites_config(self):
        """Sites configuration save karta hai"""
        os.makedirs('publishing_data', exist_ok=True)
        with open('publishing_data/wordpress_sites.json', 'w', encoding='utf-8') as f:
            json.dump(self.wordpress_sites, f, indent=2, ensure_ascii=False)
    
    def load_sites_config(self):
        """Saved sites configuration load karta hai"""
        try:
            with open('publishing_data/wordpress_sites.json', 'r', encoding='utf-8') as f:
                self.wordpress_sites = json.load(f)
        except FileNotFoundError:
            self.wordpress_sites = []
    
    def queue_content_for_publishing(self, content_data, site_names=None, schedule_time=None):
        """Content ko publishing queue mein add karta hai"""
        queue_item = {
            'id': f"pub_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'content': content_data,
            'target_sites': site_names or [site['name'] for site in self.wordpress_sites],
            'schedule_time': schedule_time,
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'attempts': 0,
            'results': {}
        }
        
        self.publishing_queue.append(queue_item)
        self.save_publishing_queue()
        return queue_item
    
    def save_publishing_queue(self):
        """Publishing queue save karta hai"""
        os.makedirs('publishing_data', exist_ok=True)
        with open('publishing_data/publishing_queue.json', 'w', encoding='utf-8') as f:
            json.dump(self.publishing_queue, f, indent=2, ensure_ascii=False)
    
    def load_publishing_queue(self):
        """Publishing queue load karta hai"""
        try:
            with open('publishing_data/publishing_queue.json', 'r', encoding='utf-8') as f:
                self.publishing_queue = json.load(f)
        except FileNotFoundError:
            self.publishing_queue = []
    
    def publish_content(self, content_data, site_name):
        """Single site par content publish karta hai"""
        site = next((s for s in self.wordpress_sites if s['name'] == site_name), None)
        if not site:
            return {'error': f'Site {site_name} not found'}
        
        try:
            client = Client(site['xmlrpc_url'], site['username'], site['password'])
            
            # Create WordPress post
            post = WordPressPost()
            post.title = content_data.get('title', 'Untitled Post')
            post.content = content_data.get('content', '')
            post.post_status = content_data.get('status', 'draft')  # draft, publish
            post.terms_names = {
                'post_tag': content_data.get('tags', []),
                'category': content_data.get('categories', ['Uncategorized'])
            }
            
            # Set featured image if provided
            if content_data.get('featured_image_path'):
                try:
                    media_id = self.upload_media(client, content_data['featured_image_path'])
                    if media_id:
                        post.thumbnail = media_id
                except Exception as e:
                    print(f"Failed to upload featured image: {e}")
            
            # Publish post
            post_id = client.call(NewPost(post))
            
            return {
                'success': True,
                'post_id': post_id,
                'site': site_name,
                'published_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'site': site_name
            }
    
    def upload_media(self, client, file_path):
        """WordPress mein media upload karta hai"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            filename = os.path.basename(file_path)
            
            data = {
                'name': filename,
                'type': 'image/jpeg',  # Adjust based on file type
                'bits': base64.b64encode(file_data).decode('utf-8')
            }
            
            response = client.call(UploadFile(data))
            return response['id']
            
        except Exception as e:
            print(f"Media upload failed: {e}")
            return None
    
    def process_publishing_queue(self):
        """Publishing queue ko process karta hai"""
        self.load_publishing_queue()
        
        for queue_item in self.publishing_queue:
            if queue_item['status'] != 'queued':
                continue
            
            # Check if scheduled time has passed
            if queue_item.get('schedule_time'):
                schedule_time = datetime.fromisoformat(queue_item['schedule_time'])
                if datetime.now() < schedule_time:
                    continue
            
            queue_item['status'] = 'processing'
            queue_item['attempts'] += 1
            
            # Publish to all target sites
            for site_name in queue_item['target_sites']:
                result = self.publish_content(queue_item['content'], site_name)
                queue_item['results'][site_name] = result
            
            # Update status
            successful_publishes = sum(1 for r in queue_item['results'].values() if r.get('success'))
            if successful_publishes > 0:
                queue_item['status'] = 'completed'
            else:
                queue_item['status'] = 'failed'
            
            queue_item['processed_at'] = datetime.now().isoformat()
        
        self.save_publishing_queue()
    
    def create_content_from_scrape(self, scraped_data, ai_generated_content):
        """Scraped data aur AI content se WordPress ready content banata hai"""
        content_data = {
            'title': ai_generated_content.get('title', 'Generated Article'),
            'content': ai_generated_content.get('content', ''),
            'tags': ai_generated_content.get('keywords', []),
            'categories': ['AI Generated', 'SEO Optimized'],
            'status': 'draft',  # Always start as draft
            'meta_description': ai_generated_content.get('meta_description', ''),
            'source_url': scraped_data.get('url', ''),
            'generated_at': datetime.now().isoformat()
        }
        
        return content_data
    
    def get_publishing_stats(self):
        """Publishing statistics return karta hai"""
        self.load_publishing_queue()
        
        total_queued = len([q for q in self.publishing_queue if q['status'] == 'queued'])
        total_completed = len([q for q in self.publishing_queue if q['status'] == 'completed'])
        total_failed = len([q for q in self.publishing_queue if q['status'] == 'failed'])
        
        return {
            'total_items': len(self.publishing_queue),
            'queued': total_queued,
            'completed': total_completed,
            'failed': total_failed,
            'success_rate': (total_completed / len(self.publishing_queue) * 100) if self.publishing_queue else 0
        }