import threading
import time
import sys
import requests

def run_server():
    sys.argv = ['webui', '--no-browser', '--port', '8899']
    from news_collector.webui import serve
    from pathlib import Path
    serve(root_dir=Path('.'), settings_path=Path('SETTINGS.yaml'), port=8899, open_browser=False)

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(3)

try:
    r = requests.get('http://127.0.0.1:8899/', timeout=5)
    print('Server response:', r.status_code)
    print('Has RTL:', 'dir="rtl"' in r.text)
    print('Has Vazirmatn:', 'Vazirmatn-Variable.woff2' in r.text)
    print('Has filter bar:', 'filter-bar' in r.text)
    print('Has reader toggle:', 'readerToggle' in r.text)
    print('Has export dropdown:', 'export-dropdown' in r.text)
except Exception as e:
    print('Error:', e)