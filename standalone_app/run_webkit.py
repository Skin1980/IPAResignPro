#!/usr/bin/env python3
"""
IPAResignPro - Native Desktop App runner powered by WebKit (WKWebView).
Renders the complete, responsive UI using Apple's native WebKit engine in a desktop window.
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

# Always change cwd away from root '/' when started from Finder
os.chdir(str(Path.home()))

import webview
from gui_app import app

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def wait_for_server(port, timeout=8.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False

if __name__ == "__main__":
    port = get_free_port()
    
    flask_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()

    # Ensure Flask server is up and listening
    wait_for_server(port)

    # Open modern native macOS WebKit window
    window = webview.create_window(
        title="IPAResign Pro",
        url=f"http://127.0.0.1:{port}",
        width=960,
        height=740,
        resizable=True,
        min_size=(800, 600)
    )
    webview.start()
