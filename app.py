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
    page = request.args.get('page', default=1, type=int)
    results_per_page = 25
    
    if not query:
        return {"error": "Veuillez fournir un paramètre scribd"}, 400
    
    # URL de recherche Scribd
    from urllib.parse import quote
    search_url = f"https://www.scribd.com/search?query={quote(query)}&content_type=documents"
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # On désactive les images pour accélérer le chargement
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(search_url)
        
        # On réduit le scroll au strict nécessaire pour la page demandée
        # Scribd charge souvent pas mal de résultats par scroll
        if page > 1:
            scroll_count = min(page, 4) # On limite à 4 scrolls max
            for _ in range(scroll_count):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.8) # Temps d'attente réduit
        else:
            time.sleep(1.5) # Juste un petit temps pour la page 1
            
        results = []
        items = driver.find_elements(By.CSS_SELECTOR, "div[data-resource_id], .document_card, .doc_card")
        
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/document/']")

        for item in items:
            try:
                if item.tag_name == 'a':
                    link = item.get_attribute("href")
                    title = item.text or "Document sans titre"
                    try:
                        img_elem = item.find_element(By.CSS_SELECTOR, "img, [class*='image'] img, [class*='thumbnail'] img")
                        image_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                    except:
                        image_url = None
                else:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".title, .doc_title, hdiv, span")
                    link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/document/']")
                    title = title_elem.text
                    link = link_elem.get_attribute("href")
                    try:
                        img_elem = item.find_element(By.CSS_SELECTOR, "img, [class*='image'] img, [class*='thumbnail'] img, .doc_card_image img")
                        image_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                    except:
                        try:
                            parent = item.find_element(By.XPATH, "..")
                            img_elem = parent.find_element(By.CSS_SELECTOR, "img")
                            image_url = img_elem.get_attribute("src") or img_elem.get_attribute("data-src")
                        except:
                            image_url = None
                
                if link and "/document/" in link:
                    if not any(r['url'] == link for r in results):
                        results.append({
                            "titre": title.strip(),
                            "url": link
                        })
            except:
                continue
        
        # Pagination logique
        total_results = len(results)
        start_idx = (page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        
        paginated_results = results[start_idx:end_idx]
                
        return {
            "query": query,
            "page": page,
            "results_per_page": results_per_page,
            "total_found": total_results,
            "count": len(paginated_results),
            "resultats": paginated_results
        }
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
    Respecte les limites de Render (750h/mois).
    """
    def ping():
        while True:
            try:
                # On utilise l'heure de Madagascar/Paris
                now = datetime.now(pytz.timezone('Indian/Antananarivo'))
                hour = now.hour
                
                # Render Free Tier offre 750h/mois, ce qui couvre 24/24 pour un mois de 31 jours (744h).
                # Cependant, pour être sûr et dynamique, on peut limiter les pings.
                # Ping toutes les 14 minutes comme demandé
                
                app_url = os.environ.get('RENDER_EXTERNAL_URL')
                if app_url:
                    requests.get(app_url)
                    print(f"[{now}] Auto-ping envoyé à {app_url}")
                
            except Exception as e:
                print(f"Erreur auto-ping: {e}")
            
            # Attendre 14 minutes (840 secondes)
            time.sleep(840)

    # Lancer le thread si on est sur Render
    if os.environ.get('RENDER'):
        thread = threading.Thread(target=ping, daemon=True)
        thread.start()

if __name__ == '__main__':
    auto_ping()
    app.run(host='0.0.0.0', port=5000)
