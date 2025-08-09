# config.py - Configuration file for SEO Dashboard

import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-super-secret-key-change-this'
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Chrome Driver Path (Update this according to your system)
    CHROME_DRIVER_PATH = os.environ.get('CHROME_DRIVER_PATH') or r"C:\Users\FCC The Gurukul\Documents\A Python Project\chromedriver-win64\chromedriver.exe"
    
    # Monitoring Configuration
    COMPETITOR_SCAN_INTERVAL = timedelta(hours=12)  # Scan competitors every 12 hours
    MAX_CONCURRENT_REQUESTS = 50
    
    # Content Generation Settings
    AI_MAX_TOKENS = 2000
    AI_TEMPERATURE = 0.7
    
    # Publishing Settings
    AUTO_PUBLISH_ENABLED = True
    DEFAULT_POST_STATUS = 'draft'  # 'draft' or 'publish'
    
    # File Paths
    SCAN_DATA_DIR = "scans"
    SCRAPED_DATA_DIR = "scraped_data"
    MONITORING_DATA_DIR = "monitoring_data"
    PUBLISHING_DATA_DIR = "publishing_data"
    
    # SEO Settings
    MIN_WORD_COUNT = 500
    TARGET_READABILITY_SCORE = 60
    MIN_SEO_SCORE = 70

# Environment-specific configurations
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}