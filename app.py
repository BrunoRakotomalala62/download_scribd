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

        # Scroll to load all pages
        page_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
        for page in page_elements:
            driver.execute_script("arguments[0].scrollIntoView();", page)
            time.sleep(0.3)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
