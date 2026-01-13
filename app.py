from flask import Flask, render_template, request, send_file, after_this_request
import os
import time
import base64
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import threading
import requests
from datetime import datetime
import pytz
from urllib.parse import quote

app = Flask(__name__)

# Stockage en mémoire des résultats de recherche pour le téléchargement par index
search_cache = {}

def convert_scribd_link(url):
    match = re.search(r'https://(?:[a-z]{2}\.)?scribd\.com/document/(\d+)/', url)
    if not match:
        # Fallback pour les liens simplifiés ou sans titre
        match = re.search(r'scribd\.com/document/(\d+)', url)
    
    if match:
        doc_id = match.group(1)
        return f'https://www.scribd.com/embeds/{doc_id}/content'
    return None

def download_scribd_pdf(url):
    embed_url = convert_scribd_link(url)
    if not embed_url:
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(embed_url)
        time.sleep(3)

        page_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
        for i in range(0, len(page_elements), 3):
            driver.execute_script("arguments[0].scrollIntoView();", page_elements[i])
            time.sleep(0.15)
        
        if page_elements:
            driver.execute_script("arguments[0].scrollIntoView();", page_elements[-1])
            time.sleep(0.2)

        driver.execute_script("""
            ['.toolbar_top', '.toolbar_bottom'].forEach(selector => {
                var el = document.querySelector(selector);
                if (el) el.parentNode.removeChild(el);
            });
            var scroller = document.querySelector('.document_scroller');
            if (scroller) scroller.setAttribute('class', '');
            
            var style = document.createElement('style');
            style.textContent = '@media print { @page { margin: 0; } }';
            document.head.appendChild(style);
        """)

        print_options = {
            'landscape': False,
            'displayHeaderFooter': False,
            'printBackground': True,
            'preferCSSPageSize': True,
        }
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        pdf_data = base64.b64decode(result['data'])
        
        filename = f"scribd_download_{int(time.time())}.pdf"
        filepath = os.path.join("/tmp", filename)
        with open(filepath, 'wb') as f:
            f.write(pdf_data)
        
        return filepath
    finally:
        driver.quit()

@app.route('/recherche')
def recherche():
    query = request.args.get('scribd')
    page = request.args.get('page', default=1, type=int)
    results_per_page = 25
    
    if not query:
        return {"error": "Veuillez fournir un paramètre scribd"}, 400
    
    search_url = f"https://www.scribd.com/search?query={quote(query)}&content_type=documents"
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(search_url)
        
        if page > 1:
            scroll_count = min(page, 4)
            for _ in range(scroll_count):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.8)
        else:
            time.sleep(1.5)
            
        results = []
        items = driver.find_elements(By.CSS_SELECTOR, "div[data-resource_id], .document_card, .doc_card")
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/document/']")

        for item in items:
            try:
                if item.tag_name == 'a':
                    link = item.get_attribute("href")
                    title = item.text or "Document sans titre"
                else:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".title, .doc_title, hdiv, span")
                    link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/document/']")
                    title = title_elem.text
                    link = link_elem.get_attribute("href")
                
                if link and "/document/" in link:
                    if not any(r['url'] == link for r in results):
                        results.append({
                            "titre": title.strip().replace('\n', ' '),
                            "url": link
                        })
            except:
                continue
        
        total_results = len(results)
        start_idx = (page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        paginated_results = results[start_idx:end_idx]
        
        # Formater les résultats avec numérotation
        formatted_results = {}
        for i, res in enumerate(paginated_results, 1):
            num = start_idx + i
            formatted_results[str(num)] = res["titre"]
            # Mettre en cache l'URL pour le téléchargement par numéro
            search_cache[str(num)] = res["url"]
                
        return formatted_results
    finally:
        driver.quit()

@app.route('/download')
def download_api():
    url_or_num = request.args.get('scribd_url')
    if not url_or_num:
        return "Veuillez fournir un paramètre scribd_url", 400
    
    # Vérifier si c'est un numéro en cache
    if url_or_num in search_cache:
        url = search_cache[url_or_num]
    else:
        url = url_or_num
    
    filepath = download_scribd_pdf(url)
    if not filepath:
        return "URL ou numéro Scribd invalide", 400

    @after_this_request
    def remove_file(response):
        try:
            os.remove(filepath)
        except Exception as error:
            app.logger.error("Error removing file", error)
        return response

    return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            return "Veuillez entrer une URL", 400
        
        filepath = download_scribd_pdf(url)
        if not filepath:
            return "URL Scribd invalide", 400

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filepath)
            except Exception as error:
                app.logger.error("Error removing file", error)
            return response

        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))

    return render_template('index.html')

def auto_ping():
    def ping():
        while True:
            try:
                now = datetime.now(pytz.timezone('Indian/Antananarivo'))
                app_url = os.environ.get('RENDER_EXTERNAL_URL')
                if app_url:
                    requests.get(app_url)
                    print(f"[{now}] Auto-ping envoyé à {app_url}")
            except Exception as e:
                print(f"Erreur auto-ping: {e}")
            time.sleep(840)

    if os.environ.get('RENDER'):
        thread = threading.Thread(target=ping, daemon=True)
        thread.start()

if __name__ == '__main__':
    auto_ping()
    app.run(host='0.0.0.0', port=5000)
