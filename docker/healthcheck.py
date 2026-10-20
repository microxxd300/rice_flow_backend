"""Docker HEALTHCHECK: exit 0 when /api/health/ answers 200, else 1.

Sends the first ALLOWED_HOSTS entry as the Host header so Django accepts the
request inside the container, wherever it is deployed.
"""
import os
import sys
import urllib.request

port = os.getenv('PORT', '8000')
host = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0].strip()
if host in ('', '*') or host.startswith('.'):
    host = 'localhost'

req = urllib.request.Request(f'http://127.0.0.1:{port}/api/health/', headers={'Host': host})
try:
    with urllib.request.urlopen(req, timeout=4) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
