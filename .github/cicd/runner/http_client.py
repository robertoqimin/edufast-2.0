import json
import urllib.request

def request(url, context, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, context=context, timeout=15) as response:
        return response.status, dict(response.headers), response.read()
