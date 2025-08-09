# competitor_monitor.py

import asyncio
import aiohttp
import schedule
import time
import json
import os
from datetime import datetime, timedelta
from analyzer_logic import get_all_sitemap_urls, check_url_health
from ai_content_generator import AIContentGenerator
import threading

class CompetitorMonitor:
    def __init__(self):
        self.competitors = []
        self.monitoring_data = {}
        self.ai_generator = AIContentGenerator()
        self.monitoring_active = False
        
    def add_competitor(self, name, url, keywords=None):
        """Competitor add karta hai monitoring list mein"""
        competitor = {
            'name': name,
            'url': url,
            'keywords': keywords or [],
            'added_date': datetime.now().isoformat(),
            'last_scan': None,
            'content_changes': [],
            'new_content_detected': []
        }
        self.competitors.append(competitor)
        self.save_competitors()
        return competitor
    
    def save_competitors(self):
        """Competitors list ko file mein save karta hai"""
        os.makedirs('monitoring_data', exist_ok=True)
        with open('monitoring_data/competitors.json', 'w', encoding='utf-8') as f:
            json.dump(self.competitors, f, indent=2, ensure_ascii=False)
    
    def load_competitors(self):
        """Saved competitors load karta hai"""
        try:
            with open('monitoring_data/competitors.json', 'r', encoding='utf-8') as f:
                self.competitors = json.load(f)
        except FileNotFoundError:
            self.competitors = []
    
    async def scan_competitor(self, competitor):
        """Single competitor ko scan karta hai"""
        try:
            async with aiohttp.ClientSession() as session:
                # Sitemap URLs fetch karein
                sitemap_urls = await get_all_sitemap_urls(session, competitor['url'])
                
                # Recent content check karein (last 7 days)
                recent_content = []
                for url_data in sitemap_urls[:50]:  # Limit to first 50 URLs
                    if url_data.get('last_modified'):
                        try:
                            last_mod = datetime.fromisoformat(url_data['last_modified'].replace('Z', '+00:00'))
                            if last_mod > datetime.now() - timedelta(days=7):
                                recent_content.append(url_data)
                        except:
                            continue
                
                # Content changes detect karein
                previous_scan = competitor.get('last_scan_data', {})
                current_urls = {item['url']: item for item in sitemap_urls}
                previous_urls = previous_scan.get('urls', {})
                
                new_content = []
                for url, data in current_urls.items():
                    if url not in previous_urls:
                        new_content.append(data)
                
                # Results save karein
                scan_result = {
                    'timestamp': datetime.now().isoformat(),
                    'total_urls': len(sitemap_urls),
                    'recent_content': recent_content,
                    'new_content': new_content,
                    'urls': current_urls
                }
                
                competitor['last_scan'] = datetime.now().isoformat()
                competitor['last_scan_data'] = scan_result
                
                # AI analysis for new content
                if new_content:
                    await self.analyze_new_content(competitor, new_content)
                
                return scan_result
                
        except Exception as e:
            print(f"Error scanning competitor {competitor['name']}: {e}")
            return None
    
    async def analyze_new_content(self, competitor, new_content):
        """New content ko AI se analyze karta hai"""
        for content_item in new_content[:5]:  # Limit to 5 new articles
            try:
                # Content scrape karein (simplified)
                async with aiohttp.ClientSession() as session:
                    async with session.get(content_item['url']) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # AI analysis
                            analysis_prompt = f"""
                            Analyze this competitor's new content and suggest how we can create better content:
                            
                            URL: {content_item['url']}
                            Content: {html[:2000]}...
                            
                            Provide:
                            1. Main topic and keywords
                            2. Content gaps we can fill
                            3. Better angle for our content
                            4. SEO opportunities
                            """
                            
                            ai_analysis = self.ai_generator.generate_content_with_ai(analysis_prompt)
                            
                            content_item['ai_analysis'] = ai_analysis
                            competitor['new_content_detected'].append(content_item)
                            
            except Exception as e:
                print(f"Error analyzing content {content_item['url']}: {e}")
    
    def start_monitoring(self):
        """Automated monitoring start karta hai"""
        self.monitoring_active = True
        
        # Schedule daily scans
        schedule.every().day.at("09:00").do(self.run_daily_scan)
        schedule.every().day.at("18:00").do(self.run_daily_scan)
        
        # Background thread for scheduler
        def run_scheduler():
            while self.monitoring_active:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        print("Competitor monitoring started!")
    
    def run_daily_scan(self):
        """Daily scan execute karta hai"""
        print("Running daily competitor scan...")
        asyncio.run(self.scan_all_competitors())
    
    async def scan_all_competitors(self):
        """Sabhi competitors ko scan karta hai"""
        self.load_competitors()
        
        for competitor in self.competitors:
            print(f"Scanning {competitor['name']}...")
            result = await self.scan_competitor(competitor)
            if result:
                print(f"Found {len(result['new_content'])} new articles from {competitor['name']}")
        
        self.save_competitors()
        
        # Generate opportunities report
        self.generate_opportunities_report()
    
    def generate_opportunities_report(self):
        """Content opportunities ka report generate karta hai"""
        opportunities = []
        
        for competitor in self.competitors:
            if competitor.get('new_content_detected'):
                for content in competitor['new_content_detected'][-5:]:  # Last 5
                    if content.get('ai_analysis'):
                        opportunities.append({
                            'competitor': competitor['name'],
                            'url': content['url'],
                            'analysis': content['ai_analysis'],
                            'detected_date': content.get('last_modified')
                        })
        
        # Save opportunities
        os.makedirs('monitoring_data', exist_ok=True)
        with open('monitoring_data/content_opportunities.json', 'w', encoding='utf-8') as f:
            json.dump(opportunities, f, indent=2, ensure_ascii=False)
        
        return opportunities
    
    def get_content_suggestions(self, topic_keywords):
        """Topic ke basis par content suggestions deta hai"""
        suggestions = []
        
        for competitor in self.competitors:
            if competitor.get('last_scan_data'):
                # Check if any competitor covered this topic
                for url_data in competitor['last_scan_data']['urls'].values():
                    url_lower = url_data['url'].lower()
                    if any(keyword.lower() in url_lower for keyword in topic_keywords):
                        suggestions.append({
                            'competitor': competitor['name'],
                            'url': url_data['url'],
                            'suggestion': f"Competitor ne is topic par content banaya hai. Hum better angle se likh sakte hain."
                        })
        
        return suggestions