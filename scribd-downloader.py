"""
Script to download documents from Scribd.
This script uses Selenium to convert Scribd document links to embeddable format,
scrolls through the document, removes unwanted elements, and opens the print dialog.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options   
import time


# Set up Google options
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--remote-debugging-port=9222")
# Enable Developer Tools to open automatically
# options.add_argument("-devtools")


# Convert link
def convert_scribd_link(url):
    import re
    match = re.search(r'https://(?:[a-z]{2}\.)?scribd\.com/document/(\d+)/', url)
    if match:
        doc_id = match.group(1)
        return f'https://www.scribd.com/embeds/{doc_id}/content'
    else:
        return "Invalid Scribd URL"


# Input Scribd link
input_url = input("Input link Scribd: ")
converted_url = convert_scribd_link(input_url)
print("Link embed:", converted_url)


# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=options)


# Open the webpage
driver.get(converted_url)

# Wait for the page to load
time.sleep(2)

# STEP 01: SCROLL
# Scroll from the top to the bottom of the page
page_elements = driver.find_elements("css selector", "[class*='page']")
for page in page_elements:
    driver.execute_script("arguments[0].scrollIntoView();", page)
    time.sleep(0.5)

print("Last Page") 


time.sleep(2)


# STEP 02: DELETE DIVS - CLASS
# Delete footer top & bottom
toolbar_top_exists = driver.execute_script("""
        var toolbarTop = document.querySelector('.toolbar_top');
        if (toolbarTop) {
            toolbarTop.parentNode.removeChild(toolbarTop);
            return true;  // Indicate that it was removed
        }
        return false;  // Indicate that it was not found
    """)

# Debug message for toolbar_top
if toolbar_top_exists:
    print("'toolbar_top' was successfully deleted.")
else:
    print("'toolbar_top' was not found.")

# Check and delete toolbar_bottom
toolbar_bottom_exists = driver.execute_script("""
    var toolbarBottom = document.querySelector('.toolbar_bottom');
    if (toolbarBottom) {
        toolbarBottom.parentNode.removeChild(toolbarBottom);
        return true;  // Indicate that it was removed
    }
    return false;           // Indicate that it was not found
""")

# Debug message for toolbar_bottom
if toolbar_bottom_exists:
    print("✅ 'toolbar_bottom' was successfully deleted.")
else:
    print("❌ 'toolbar_bottom' was not found.") 

# Deleting container:
elements = driver.find_elements(By.CLASS_NAME, "document_scroller")

# Loop through each element and change its class
for element in elements:
    driver.execute_script("arguments[0].setAttribute('class', '');", element)

print("  -------  Deleted containers  ----------")


# STEP 03: INJECT PRINT CSS
# Add CSS to remove margins when printing (no whitespace around pages)
driver.execute_script("""
    var style = document.createElement('style');
    style.id = 'scribd-print-styles';
    style.textContent = `
        @media print {
            @page {
                margin: 0;
            }
            .toolbar_top, .toolbar_bottom {
                display: none !important;
            }
        }
    `;
    document.head.appendChild(style);
""")
print("✅ Print CSS injected (no margins)")


import base64
import json

# STEP 04: PRINT PDF using CDP
# Scroll back to top
driver.execute_script("window.scrollTo(0, 0);")

print("⏳ Génération du PDF en cours...")

# Utiliser Chrome DevTools Protocol pour générer le PDF
print_options = {
    'landscape': False,
    'displayHeaderFooter': False,
    'printBackground': True,
    'preferCSSPageSize': True,
}

result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
pdf_data = base64.b64decode(result['data'])

# Sauvegarder le fichier
filename = f"scribd_download_{int(time.time())}.pdf"
with open(filename, 'wb') as f:
    f.write(pdf_data)

print(f"✅ PDF généré avec succès : {filename}")
print(f"Vous pouvez maintenant télécharger le fichier '{filename}' depuis l'explorateur de fichiers à gauche.")

driver.quit()
