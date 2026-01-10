# Comment utiliser Scribd Downloader

Ce script vous permet de télécharger des documents Scribd en les convertissant au format "embed", ce qui permet d'afficher tout le contenu sans restrictions, puis en utilisant la fonction d'impression du navigateur pour sauvegarder en PDF.

## Étapes pour télécharger :

1. **Lancer le script** : Cliquez sur le bouton "Run" dans Replit.
2. **Entrer l'URL** : Le script vous demandera "Input link Scribd: ". Collez l'URL complète du document (ex: `https://www.scribd.com/document/123456/Titre-du-Doc`).
3. **Traitement** : 
   - Le script va automatiquement faire défiler tout le document pour charger toutes les pages.
   - Il va supprimer les barres d'outils et éléments inutiles pour un PDF propre.
   - Il injecte du code CSS pour supprimer les marges blanches.
4. **Sauvegarde** :
   - Le script ouvre la boîte de dialogue d'impression (`window.print()`).
   - **Important** : Comme Replit s'exécute sur un serveur, l'impression se fait dans le navigateur virtuel.

## Exemple d'URL valide :
`https://www.scribd.com/document/511874311/The-Art-of-War-by-Sun-Tzu`
