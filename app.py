from flask import Flask, render_template, request, send_file, after_this_request
import os
import time
import base64
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)

def convert_scribd_link(url):
    match = re.search(r'https://(?:[a-z]{2}\.)?scribd\.com/document/(\d+)/', url)
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

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(embed_url)
        time.sleep(3)

        # Scroll to load all pages faster
        page_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
        # Batch scrolling or faster scroll
        for i in range(0, len(page_elements), 3):  # Scroll every 3 pages
            driver.execute_script("arguments[0].scrollIntoView();", page_elements[i])
            time.sleep(0.15)
        
        # Ensure last page is loaded
        if page_elements:
            driver.execute_script("arguments[0].scrollIntoView();", page_elements[-1])
            time.sleep(0.2)

        # Cleanup UI
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

@app.route('/download')
def download_api():
    url = request.args.get('scribd_url')
    if not url:
        return "Veuillez fournir un paramètre scribd_url", 400
    
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

@app.route('/recherche')
def recherche():
    query = request.args.get('scribd')
    if not query:
        return {"error": "Veuillez fournir un paramètre scribd"}, 400
    
    # URL de recherche Scribd
    from urllib.parse import quote
    search_url = f"https://www.scribd.com/search?query={quote(query)}&content_type=documents"
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(search_url)
        time.sleep(3)
        
        results = []
        # On essaie des sélecteurs plus génériques
        # Scribd change souvent ses classes, on cherche par structure
        # Les cartes de documents sont souvent des div avec des attributs spécifiques
        items = driver.find_elements(By.CSS_SELECTOR, "div[data-resource_id], .document_card, .doc_card")
        
        if not items:
            # Fallback sur les liens qui ressemblent à des documents
            items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/document/']")

        for item in items[:15]:
            try:
                # Si l'item est déjà le lien
                if item.tag_name == 'a':
                    link = item.get_attribute("href")
                    title = item.text or "Document sans titre"
                else:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".title, .doc_title, hdiv, span")
                    link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/document/']")
                    title = title_elem.text
                    link = link_elem.get_attribute("href")
                
                if link and "/document/" in link:
                    # Éviter les doublons
                    if not any(r['url'] == link for r in results):
                        results.append({
                            "titre": title.strip(),
                            "url": link
                        })
            except:
                continue
                
        return {"resultats": results, "count": len(results)}
    finally:
        driver.quit()

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

import threading
import requests
from datetime import datetime
import pytz

def auto_ping():
    """
    Fonction pour auto-ping l'application afin de la maintenir éveillée sur Render.
    Respecte les plages horaires demandées (06h-00h).
    """
    def ping():
        while True:
            try:
                # On utilise l'heure de Madagascar/Paris ou UTC selon besoin, ici UTC+3 (proche Madagascar/France été)
                # On peut aussi laisser l'utilisateur configurer sa timezone. Par défaut UTC.
                now = datetime.now(pytz.timezone('Indian/Antananarivo'))
                hour = now.hour
                
                # De 06h00 à 00h00 : Mode éveil (ping toutes les 10 minutes)
                if 6 <= hour < 24:
                    app_url = os.environ.get('RENDER_EXTERNAL_URL')
                    if app_url:
                        requests.get(app_url)
                        print(f"[{now}] Auto-ping envoyé à {app_url}")
                
                # De 00h00 à 06h00 : On laisse dormir (pas de ping)
                
            except Exception as e:
                print(f"Erreur auto-ping: {e}")
            
            # Attendre 10 minutes (600 secondes)
            time.sleep(600)

    # Lancer le thread si on est sur Render
    if os.environ.get('RENDER'):
        thread = threading.Thread(target=ping, daemon=True)
        thread.start()

if __name__ == '__main__':
    auto_ping()
    app.run(host='0.0.0.0', port=5000)
