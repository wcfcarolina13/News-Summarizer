"""
Web interface for Data CSV Processor.
Mobile-friendly interface for processing newsletters and web sources into CSV.

Run locally: python web_app.py
Deploy to: Railway, Render, Replit, or any Python hosting service
"""

import os
import io
import csv
import json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file, Response
from data_csv_processor import (
    DataCSVProcessor,
    ExtractionConfig,
    ExtractedItem,
    load_custom_instructions
)

app = Flask(__name__)

# Store extracted data in memory (for demo; use database for production)
extraction_history = []

# Mobile-friendly HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Data CSV Processor</title>
    <style>
        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            margin: 0;
            padding: 16px;
            min-height: 100vh;
        }

        .container {
            max-width: 600px;
            margin: 0 auto;
        }

        h1 {
            font-size: 1.5rem;
            margin: 0 0 8px 0;
            color: #fff;
        }

        .subtitle {
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 20px;
        }

        .card {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid #333;
        }

        label {
            display: block;
            font-size: 0.85rem;
            color: #aaa;
            margin-bottom: 8px;
        }

        textarea, input[type="text"], select {
            width: 100%;
            padding: 14px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #252525;
            color: #fff;
            font-size: 16px; /* Prevents zoom on iOS */
            margin-bottom: 12px;
            resize: vertical;
        }

        textarea:focus, input:focus, select:focus {
            outline: none;
            border-color: #4a9eff;
        }

        textarea {
            min-height: 100px;
        }

        button {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #4a9eff;
            color: #fff;
        }

        .btn-primary:hover, .btn-primary:active {
            background: #3a8eef;
        }

        .btn-primary:disabled {
            background: #333;
            color: #666;
        }

        .btn-secondary {
            background: #333;
            color: #fff;
            margin-top: 8px;
        }

        .btn-success {
            background: #2ecc71;
            color: #fff;
        }

        .status {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 0.9rem;
        }

        .status.loading {
            background: #1e3a5f;
            color: #4a9eff;
        }

        .status.success {
            background: #1e3f2e;
            color: #2ecc71;
        }

        .status.error {
            background: #3f1e1e;
            color: #e74c3c;
        }

        .results {
            margin-top: 16px;
        }

        .result-item {
            background: #252525;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 3px solid #4a9eff;
        }

        .result-item .category {
            font-size: 0.75rem;
            color: #4a9eff;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .result-item .title {
            font-weight: 500;
            margin-bottom: 4px;
            word-break: break-word;
        }

        .result-item .url {
            font-size: 0.8rem;
            color: #888;
            word-break: break-all;
        }

        .result-item a {
            color: inherit;
            text-decoration: none;
        }

        .result-count {
            text-align: center;
            padding: 12px;
            color: #888;
            font-size: 0.9rem;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }

        .tab {
            flex: 1;
            padding: 12px;
            background: #252525;
            border: 1px solid #333;
            border-radius: 8px;
            color: #888;
            font-size: 0.9rem;
            text-align: center;
            cursor: pointer;
        }

        .tab.active {
            background: #4a9eff;
            border-color: #4a9eff;
            color: #fff;
        }

        .hidden {
            display: none !important;
        }

        .config-section {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #333;
        }

        .toggle-config {
            background: none;
            border: none;
            color: #4a9eff;
            font-size: 0.85rem;
            padding: 8px 0;
            cursor: pointer;
            width: auto;
        }

        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .checkbox-row input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin: 0;
        }

        .checkbox-row label {
            margin: 0;
            color: #e0e0e0;
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #4a9eff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .quick-source {
            display: inline-block;
            padding: 8px 12px;
            background: #333;
            border-radius: 16px;
            font-size: 0.8rem;
            margin: 4px;
            cursor: pointer;
        }

        .quick-source:hover {
            background: #444;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Data CSV Processor</h1>
        <p class="subtitle">Extract links from newsletters & web pages</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('url')">URL</div>
            <div class="tab" onclick="switchTab('html')">Paste HTML</div>
        </div>

        <form id="extractForm">
            <div class="card">
                <div id="urlTab">
                    <label for="url">Newsletter or Web Page URL</label>
                    <input type="text" id="url" name="url" placeholder="https://cryptosum.beehiiv.com/p/...">
                </div>

                <div id="htmlTab" class="hidden">
                    <label for="html">Paste HTML Content</label>
                    <textarea id="html" name="html" placeholder="Paste the HTML source here (View Source from browser)..."></textarea>
                    <label for="sourceUrl">Source URL (for metadata)</label>
                    <input type="text" id="sourceUrl" name="sourceUrl" placeholder="https://example.com/newsletter">
                </div>

                <label for="config">Extraction Config</label>
                <select id="config" name="config">
                    <option value="default">Default (all links)</option>
                    <option value="cryptosum" selected>CryptoSum Newsletter</option>
                    <option value="custom">Custom...</option>
                </select>

                <button type="button" class="toggle-config" onclick="toggleConfig()">
                    Advanced Options
                </button>

                <div id="configSection" class="config-section hidden">
                    <div class="checkbox-row">
                        <input type="checkbox" id="stripTracking" checked>
                        <label for="stripTracking">Strip tracking params (utm_*, etc.)</label>
                    </div>
                    <div class="checkbox-row">
                        <input type="checkbox" id="resolveRedirects">
                        <label for="resolveRedirects">Resolve redirects (slower)</label>
                    </div>
                    <label for="blockedDomains">Blocked domains (comma-separated)</label>
                    <input type="text" id="blockedDomains" placeholder="twitter.com, facebook.com">
                </div>

                <button type="submit" class="btn-primary" id="extractBtn">
                    Extract Links
                </button>
            </div>
        </form>

        <div id="status" class="status hidden"></div>

        <div id="results" class="hidden">
            <div class="card">
                <div class="result-count" id="resultCount"></div>
                <button class="btn-success" onclick="downloadCSV()">
                    Download CSV
                </button>
                <button class="btn-secondary" onclick="copyToClipboard()">
                    Copy as Text
                </button>
            </div>

            <div class="results" id="resultsList"></div>
        </div>
    </div>

    <script>
        let extractedItems = [];
        let currentTab = 'url';

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.getElementById('urlTab').classList.toggle('hidden', tab !== 'url');
            document.getElementById('htmlTab').classList.toggle('hidden', tab !== 'html');
        }

        function toggleConfig() {
            const section = document.getElementById('configSection');
            section.classList.toggle('hidden');
        }

        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.className = 'status ' + type;
            status.innerHTML = type === 'loading' ? '<span class="spinner"></span>' + message : message;
            status.classList.remove('hidden');
        }

        function hideStatus() {
            document.getElementById('status').classList.add('hidden');
        }

        document.getElementById('extractForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const btn = document.getElementById('extractBtn');
            btn.disabled = true;
            showStatus('Extracting links...', 'loading');
            document.getElementById('results').classList.add('hidden');

            try {
                const formData = {
                    mode: currentTab,
                    url: document.getElementById('url').value,
                    html: document.getElementById('html').value,
                    sourceUrl: document.getElementById('sourceUrl').value,
                    config: document.getElementById('config').value,
                    stripTracking: document.getElementById('stripTracking').checked,
                    resolveRedirects: document.getElementById('resolveRedirects').checked,
                    blockedDomains: document.getElementById('blockedDomains').value
                };

                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                } else {
                    extractedItems = data.items;
                    showResults(data.items);
                    showStatus('Extracted ' + data.items.length + ' links', 'success');
                }
            } catch (err) {
                showStatus('Error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
            }
        });

        function showResults(items) {
            const results = document.getElementById('results');
            const list = document.getElementById('resultsList');
            const count = document.getElementById('resultCount');

            count.textContent = items.length + ' links extracted';

            list.innerHTML = items.map(item => `
                <div class="result-item">
                    <div class="category">${item.category || 'General'}</div>
                    <div class="title">${item.title || 'Untitled'}</div>
                    <div class="url"><a href="${item.url}" target="_blank">${item.url}</a></div>
                </div>
            `).join('');

            results.classList.remove('hidden');
        }

        function downloadCSV() {
            if (!extractedItems.length) return;

            // Create CSV content
            const headers = ['title', 'url', 'category', 'source_name', 'date_published'];
            const rows = extractedItems.map(item =>
                headers.map(h => '"' + (item[h] || '').replace(/"/g, '""') + '"').join(',')
            );
            const csv = [headers.join(','), ...rows].join('\\n');

            // Download
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'extracted_' + new Date().toISOString().slice(0,10) + '.csv';
            a.click();
            URL.revokeObjectURL(url);
        }

        function copyToClipboard() {
            if (!extractedItems.length) return;

            const text = extractedItems.map(item =>
                `[${item.category}] ${item.title}\\n${item.url}`
            ).join('\\n\\n');

            navigator.clipboard.writeText(text).then(() => {
                showStatus('Copied to clipboard!', 'success');
                setTimeout(hideStatus, 2000);
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/extract', methods=['POST'])
def extract():
    """Extract links from URL or HTML content."""
    try:
        data = request.json
        mode = data.get('mode', 'url')

        # Build config
        config = ExtractionConfig(
            resolve_redirects=data.get('resolveRedirects', False),
            strip_tracking_params=data.get('stripTracking', True),
            timeout=15
        )

        processor = DataCSVProcessor(config)

        # Load extraction instructions based on config selection
        config_name = data.get('config', 'default')
        custom_instructions = None

        if config_name == 'cryptosum':
            config_path = os.path.join(os.path.dirname(__file__),
                                       'extraction_instructions', 'cryptosum.json')
            if os.path.exists(config_path):
                custom_instructions = load_custom_instructions(config_path)

        # Add any custom blocked domains
        blocked = data.get('blockedDomains', '')
        if blocked and custom_instructions is None:
            custom_instructions = {}
        if blocked:
            blocked_list = [d.strip() for d in blocked.split(',') if d.strip()]
            if custom_instructions:
                existing = custom_instructions.get('blocked_domains', [])
                custom_instructions['blocked_domains'] = list(set(existing + blocked_list))

        # Extract based on mode
        if mode == 'html':
            html = data.get('html', '')
            source_url = data.get('sourceUrl', '')
            if not html:
                return jsonify({'error': 'No HTML content provided'})
            items = processor.process_html(html, source_url, custom_instructions)
        else:
            url = data.get('url', '').strip()
            if not url:
                return jsonify({'error': 'No URL provided'})
            if not url.startswith('http'):
                url = 'https://' + url
            items = processor.process_url(url, custom_instructions)

        # Convert to JSON-serializable format
        result_items = []
        for item in items:
            result_items.append({
                'title': item.title,
                'url': item.url,
                'category': item.category,
                'source_name': item.source_name,
                'description': item.description,
                'date_published': item.date_published,
                'date_extracted': item.date_extracted
            })

        # Store in history
        extraction_history.append({
            'timestamp': datetime.now().isoformat(),
            'source': data.get('url') or data.get('sourceUrl') or 'html',
            'count': len(result_items),
            'items': result_items
        })

        return jsonify({
            'items': result_items,
            'count': len(result_items)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<int:index>')
def download_csv(index):
    """Download extraction results as CSV."""
    try:
        if index >= len(extraction_history):
            return "Not found", 404

        items = extraction_history[index]['items']

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'title', 'url', 'category', 'source_name', 'date_published'
        ])
        writer.writeheader()
        for item in items:
            writer.writerow({
                'title': item['title'],
                'url': item['url'],
                'category': item['category'],
                'source_name': item['source_name'],
                'date_published': item['date_published']
            })

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=extracted_{index}.csv'}
        )
    except Exception as e:
        return str(e), 500


@app.route('/api/configs')
def list_configs():
    """List available extraction configs."""
    configs_dir = os.path.join(os.path.dirname(__file__), 'extraction_instructions')
    configs = []

    if os.path.exists(configs_dir):
        for f in os.listdir(configs_dir):
            if f.endswith('.json') and not f.startswith('_'):
                name = f.replace('.json', '')
                configs.append(name)

    return jsonify({'configs': configs})


@app.route('/health')
def health():
    """Health check endpoint for deployment platforms."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\n{'='*50}")
    print("  Data CSV Processor - Web Interface")
    print(f"{'='*50}")
    print(f"\n  Local:   http://localhost:{port}")
    print(f"  Network: http://0.0.0.0:{port}")
    print(f"\n  Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
