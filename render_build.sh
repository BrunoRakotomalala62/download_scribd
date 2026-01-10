#!/usr/bin/env bash
# Script pour installer Google Chrome et ChromeDriver sur Render

# Créer un dossier pour les binaires
mkdir -p $HOME/.bin

# Télécharger et installer Chrome
if [[ ! -f $HOME/.bin/chrome ]]; then
    echo "Installing Chrome..."
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    dpkg -x google-chrome-stable_current_amd64.deb $HOME/.chrome
    ln -sf $HOME/.chrome/opt/google/chrome/google-chrome $HOME/.bin/chrome
    rm google-chrome-stable_current_amd64.deb
fi

# Télécharger et installer ChromeDriver
if [[ ! -f $HOME/.bin/chromedriver ]]; then
    echo "Installing ChromeDriver..."
    # On récupère la version de chrome installée
    CHROME_VERSION=$($HOME/.bin/chrome --version | cut -d ' ' -f 3)
    wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chromedriver-linux64.zip"
    unzip chromedriver-linux64.zip
    mv chromedriver-linux64/chromedriver $HOME/.bin/chromedriver
    rm -rf chromedriver-linux64 chromedriver-linux64.zip
fi

export PATH=$PATH:$HOME/.bin

# Installer les dépendances Python
pip install -r requirements.txt

# Lancer l'application
python app.py
