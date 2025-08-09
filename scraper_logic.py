# scraper_logic.py

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from bs4 import BeautifulSoup
import requests
import random

SCRAPED_DATA_DIR = "scraped_data"

# <<<<< ❗❗❗ IMPORTANT ❗❗❗ >>>>>
# Apne system par chromedriver ka sahi path dein
CHROME_DRIVER_PATH = r"C:\Users\FCC The Gurukul\Documents\A Python Project\chromedriver-win64\chromedriver.exe" 
# Example: r"C:\Users\YourUser\Documents\chromedriver-win64\chromedriver.exe"


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def run_scrape(article_url, publisher_name, task_id, status_dict):
    service = Service(CHROME_DRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1200")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        status_dict[task_id]['status'] = 'running'
        status_dict[task_id]['message'] = 'Opening URL...'
        status_dict[task_id]['progress'] = 5

        driver.get(article_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(3, 5))

        status_dict[task_id]['progress'] = 15
        status_dict[task_id]['message'] = 'Extracting content...'
        
        try:
            h1 = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip()
        except:
            h1 = driver.title

        markdown_content = f"# {clean_text(h1)}\n\n"
        
        # This detailed logic is taken from your script to find elements more reliably.
        for tag in ['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'table', 'img']:
            try:
                elements = driver.find_elements(By.TAG_NAME, tag)
                for el in elements:
                    if not el.is_displayed(): continue 
                    if tag == 'p' and clean_text(el.text):
                        markdown_content += f"{clean_text(el.text)}\n\n"
                    elif tag.startswith('h') and clean_text(el.text):
                        level = int(tag[1])
                        markdown_content += f"{'#' * level} {clean_text(el.text)}\n\n"
                    elif tag == 'img':
                        src = el.get_attribute('src')
                        if src and 'data:image' not in src:
                             alt = el.get_attribute('alt') or "image"
                             markdown_content += f"![{clean_text(alt)}]({urljoin(article_url, src)})\n\n"
            except StaleElementReferenceException:
                continue
        
        status_dict[task_id]['progress'] = 50
        status_dict[task_id]['message'] = 'Generating dynamic AI prompt...'

        content_lower = markdown_content.lower()
        if "recruitment" in content_lower or "apprentice" in content_lower:
            content_type, target_keywords = "Job Notification", f"{h1.lower()}, सरकारी नौकरी 2025"
        elif "tips" in content_lower or "how to" in content_lower:
            content_type, target_keywords = "Tips & Tricks", f"{h1.lower()}, गूगल रैंकिंग टिप्स"
        else:
            content_type, target_keywords = "News Article", f"{h1.lower()}, ताज़ा खबर"

        ai_prompt = f"""... (नमस्ते AI, मेरे पास एक लेख है जो मैंने एक वेबसाइट से लिया है। मैं चाहता हूँ कि तुम इस लेख को पढ़ो और इसे अपने शब्दों में दोबारा लिखो ताकि यह बिल्कुल नया, मूल, और Google में पहले रैंक पर आने लायक लगे। यहाँ कुछ खास बातें हैं जो तुम्हें ध्यान रखनी हैं:

    1. **भाषा**: बहुत ही सरल और आसान हिंदी में लिखना, जैसे कोई दोस्त बात कर रहा हो, ताकि हर कोई समझ सके और लगे कि इंसान ने लिखा है, न कि AI ने।
    2. **SEO फोकस**: लेख को Google रैंकिंग और इंडेक्सिंग के लिए ऑप्टिमाइज़ करना। इसके लिए इन कीवर्ड्स का सही इस्तेमाल करना: '{target_keywords}'। कीवर्ड्स को टाइटल, सबहेडिंग्स (H2, H3), और बॉडी में 2-3 बार naturally डालना, पर कीवर्ड स्टफिंग न करना।
    3. **लेख का प्रकार**: यह एक '{content_type}' लेख है। इसे पढ़कर उसी के हिसाब से भावनाएँ जोड़ना (जैसे उत्साह, जरूरत का अहसास), ताकि लोग इसे पसंद करें और शेयर करें।
    4. **परिचय**: लेख की शुरुआत में एक छोटा सा परिचय देना जो पाठकों का ध्यान खींचे और मुख्य विषय को समझाए।
    5. **महत्वपूर्ण जानकारी**: लेख में दी गई तारीख, समय, घोषणा, कदम (steps), और दूसरी जरूरी बातों को समझना और अपने तरीके से लिखना, पर मूल संदेश वही रखना।
    6. **बेहतर और आकर्षक बनाना**: मूल लेख से भी अच्छा बनाना। नई पंक्तियाँ, रोचक शब्द, और आसान भाषा जोड़कर इसे मजेदार बनाना, ताकि लोग पूरा पढ़ें।
    7. **इमेज प्लेसमेंट**: बताना कि इमेज कहाँ-कहाँ लगानी चाहिए (जैसे परिचय के बाद, हर सबहेडिंग के नीचे या स्टेप्स के साथ), और हर इमेज के लिए alt text में कीवर्ड डालना।
    8. **प्रकाशक का नाम**: लेख के अंत में लिखना कि '{publisher_name}' इस लेख पर आपकी राय, पसंद या समर्थन चाहता है।
    9. **SEO टिप्स**: टाइटल 60 अक्षरों से कम रखना, मेटा डिस्क्रिप्शन 150-160 अक्षरों में लिखना, और LSI कीवर्ड्स (जैसे लेख से संबंधित शब्द जो मूल में न हों, मिसाल के तौर पर 'जॉब अपडेट', 'आवेदन कैसे करें') डालना।
    10. **उन्नत निष्कर्ष**: लेख के अंत में एक निष्कर्ष देना जो पाठकों को कुछ करने के लिए प्रेरित करे (जैसे आवेदन करना, शेयर करना) और मुख्य बिंदुओं को दोहराए।

    यहाँ मूल लेख है जो तुम्हें दोबारा लिखना है:\n\n{markdown_content}\n\n
    अब इसे नए तरीके से लिखो और अंत में एक टेबल देना जिसमें ये हों:
    - **Content**: नया लिखा हुआ लेख
    - **Keywords**: इस्तेमाल किए गए मुख्य कीवर्ड्स
    - **Title Suggestion**: आकर्षक टाइटल (60 अक्षरों से कम)
    - **Tags**: संबंधित टैग्स (5-7)) ..."""

        status_dict[task_id]['progress'] = 70
        status_dict[task_id]['message'] = 'Downloading images...'
        
        domain_name = urlparse(article_url).netloc.replace('.', '-')
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_path = os.path.join(SCRAPED_DATA_DIR, f"{timestamp}_{domain_name}")
        os.makedirs(save_path, exist_ok=True)
        image_folder = os.path.join(save_path, "images")
        os.makedirs(image_folder, exist_ok=True)
        
        scraped_file = os.path.join(save_path, "scraped_content.md")
        with open(scraped_file, "w", encoding="utf-8") as f: f.write(markdown_content)
        prompt_file = os.path.join(save_path, "ai_prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as f: f.write(ai_prompt)

        images_on_page = driver.find_elements(By.TAG_NAME, "img")
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        headers = {'User-Agent': 'Mozilla/5.0 ...'}

        for index, img_el in enumerate(images_on_page):
            try:
                if not img_el.is_displayed(): continue
                img_url = img_el.get_attribute("src")
                if not img_url or "data:image" in img_url or ".svg" in img_url: continue
                
                img_url = urljoin(article_url, img_url)
                response = requests.get(img_url, headers=headers, cookies=cookies, stream=True, timeout=10)
                if response.status_code == 200 and response.content:
                    img_name = f"image_{index}.{img_url.split('.')[-1].split('?')[0] or 'jpg'}"
                    img_path = os.path.join(image_folder, img_name)
                    with open(img_path, "wb") as f: f.write(response.content)
            except Exception as e:
                print(f"Could not download image {img_url}: {e}")

        status_dict[task_id]['progress'] = 100
        status_dict[task_id].update({
            'status': 'complete', 'message': 'Scraping successful!', 'scraped_file': scraped_file,
            'prompt_file': prompt_file, 'image_folder': image_folder
        })
    except Exception as e:
        status_dict[task_id]['status'] = 'error'
        status_dict[task_id]['message'] = f"An error occurred: {str(e)}"
    finally:
        driver.quit()