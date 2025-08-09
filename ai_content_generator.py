# ai_content_generator.py

import openai
import os
import json
import re
from datetime import datetime
import textstat
import yake
from bs4 import BeautifulSoup

class AIContentGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def analyze_content_quality(self, content):
        """Content ki SEO quality analyze karta hai"""
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Basic SEO metrics
        word_count = len(text.split())
        readability_score = textstat.flesch_reading_ease(text)
        
        # Keyword extraction
        kw_extractor = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.7, top=10)
        keywords = kw_extractor.extract_keywords(text)
        
        # SEO Score calculation
        seo_score = 0
        if word_count > 300: seo_score += 20
        if word_count > 1000: seo_score += 10
        if readability_score > 60: seo_score += 20
        if len(keywords) > 5: seo_score += 15
        
        # Header analysis
        headers = soup.find_all(['h1', 'h2', 'h3'])
        if len(headers) > 3: seo_score += 15
        
        # Meta description check
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and len(meta_desc.get('content', '')) > 120: seo_score += 20
        
        return {
            'word_count': word_count,
            'readability_score': readability_score,
            'seo_score': min(seo_score, 100),
            'keywords': [kw[1] for kw in keywords[:5]],
            'headers_count': len(headers),
            'recommendations': self._get_recommendations(seo_score, word_count, readability_score)
        }
    
    def _get_recommendations(self, seo_score, word_count, readability_score):
        recommendations = []
        if seo_score < 70:
            recommendations.append("SEO score improve karne ke liye more keywords add karein")
        if word_count < 500:
            recommendations.append("Content length badhayein - minimum 500 words")
        if readability_score < 60:
            recommendations.append("Content ko simple aur readable banayein")
        return recommendations
    
    def generate_content_with_ai(self, prompt, max_tokens=2000):
        """OpenAI se content generate karta hai"""
        if not self.api_key:
            return {"error": "OpenAI API key not configured"}
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert Hindi content writer specializing in SEO-optimized articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            generated_content = response.choices[0].message.content
            
            # Content quality analyze karein
            quality_analysis = self.analyze_content_quality(generated_content)
            
            return {
                "generated_content": generated_content,
                "quality_analysis": quality_analysis,
                "tokens_used": response.usage.total_tokens,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"AI generation failed: {str(e)}"}
    
    def improve_content_seo(self, content, target_keywords):
        """Content ko SEO ke liye optimize karta hai"""
        improved_prompt = f"""
        निम्नलिखित content को SEO के लिए optimize करें:
        
        Target Keywords: {', '.join(target_keywords)}
        
        Original Content:
        {content}
        
        Requirements:
        1. Keywords को naturally integrate करें
        2. Proper H1, H2, H3 headers add करें
        3. Meta description suggest करें
        4. Content को engaging और readable बनायें
        5. Call-to-action add करें
        
        Output format:
        **Optimized Title:** 
        **Meta Description:**
        **Optimized Content:**
        """
        
        return self.generate_content_with_ai(improved_prompt, max_tokens=3000)