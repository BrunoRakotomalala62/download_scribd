# Scribd Downloader

## Overview

A tool for downloading documents from Scribd by converting document URLs to embeddable format and automating the document capture process. The project provides two approaches:

1. **Python/Selenium Script** - Server-side automation using headless Chrome to load and process Scribd documents
2. **Userscript** - Browser-based solution that runs directly in the user's browser via userscript managers like Tampermonkey

The core functionality converts standard Scribd document URLs (e.g., `scribd.com/document/123456/title`) to embed format (`scribd.com/embeds/123456/content`) which displays full content without restrictions.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### URL Conversion Pattern
- Extracts document ID from Scribd URLs using regex pattern matching
- Converts to embed endpoint format which bypasses viewing restrictions
- Pattern: `/document/{id}/` → `/embeds/{id}/content`

### Python Automation Approach
- Uses Selenium WebDriver with headless Chrome browser
- Chrome configured with specific flags for server environment:
  - `--headless=new` for modern headless mode
  - `--no-sandbox` and `--disable-dev-shm-usage` for container compatibility
  - Fixed viewport size (1920x1080) for consistent rendering
- Loads converted embed URL and waits for page rendering

### Browser Userscript Approach
- Runs client-side via Tampermonkey/Greasemonkey
- Injects floating UI button for one-click downloads
- Uses GM_* APIs for clipboard access and tab management
- Styled with CSS gradients and animations for modern appearance

### Design Decisions
- **Embed URL conversion chosen** over direct scraping because embed format loads full document content without login/subscription walls
- **Selenium over requests** because documents require JavaScript rendering and scrolling to load all pages
- **Dual-approach architecture** provides flexibility - userscript for end-users, Python script for automated/batch processing

## External Dependencies

### Python Dependencies
- **Selenium** (>=4.32.0) - Browser automation framework
- **urllib3** (<3, >=1.26) - HTTP client library (Selenium dependency)
- **trio** (~=0.17) - Async I/O library for WebSocket handling
- **trio-websocket** (~=0.9) - WebSocket client for Chrome DevTools Protocol
- **websocket-client** (~=1.8) - WebSocket communication

### Browser Requirements
- Chrome/Chromium browser installed on system
- ChromeDriver matching browser version (managed by Selenium 4.x)

### Userscript Dependencies
- Tampermonkey, Greasemonkey, or compatible userscript manager
- Requires `GM_addStyle`, `GM_setClipboard`, `GM_openInTab` grants

### External Services
- **Scribd** (scribd.com) - Target document hosting platform
- **GitHub** - Project hosting and update distribution for userscript