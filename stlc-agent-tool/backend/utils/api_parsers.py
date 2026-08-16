import re
import json
from typing import Dict, Any, List

def sanitize_json(raw_text: str) -> str:
    """
    Strips JS-style comments (// and /* */) and trailing commas from a JSON string,
    which are common in Postman exports but invalid in standard JSON.
    """
    # Remove block comments /* ... */
    text = re.sub(r'/\*.*?\*/', '', raw_text, flags=re.DOTALL)
    
    # Remove single line comments // ...
    # We must be careful not to remove http:// inside strings.
    # A simple but decent regex for JSON // comments not inside quotes
    text = re.sub(r'(?<![:"\'a-zA-Z])//.*', '', text)
    
    # Remove trailing commas
    text = re.sub(r',\s*([\]}])', r'\1', text)
    
    return text.strip()

def parse_postman_collection(raw_text: str) -> List[Dict[str, Any]]:
    clean_text = sanitize_json(raw_text)
    data = json.loads(clean_text)
    
    endpoints = []
    
    def traverse(items):
        for item in items:
            if "item" in item:
                traverse(item["item"])
            elif "request" in item:
                req = item["request"]
                name = item.get("name", "Unknown")
                method = req.get("method", "GET").upper()
                url = req.get("url", {}).get("raw", "") if isinstance(req.get("url"), dict) else req.get("url", "")
                
                headers = {}
                for h in req.get("header", []):
                    headers[h.get("key")] = h.get("value")
                    
                body = {}
                if req.get("body") and req["body"].get("mode") == "raw":
                    raw_body = req["body"].get("raw", "{}")
                    try:
                        body = json.loads(raw_body)
                    except:
                        pass
                
                endpoints.append({
                    "name": name,
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "body": body
                })
                
    traverse(data.get("item", []))
    return endpoints

def parse_curl(curl_str: str) -> List[Dict[str, Any]]:
    """
    Deterministic basic parser for curl commands to bypass LLM unreliability.
    Supports -X, -H, and -d.
    """
    endpoints = []
    
    # Very basic split handling quotes natively is complex, we use shlex
    import shlex
    try:
        parts = shlex.split(curl_str)
    except:
        parts = curl_str.split()
        
    method = "GET"
    url = ""
    headers = {}
    body = {}
    
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("http"):
            url = part
        elif part in ["-X", "--request"]:
            i += 1
            method = parts[i].upper()
        elif part in ["-H", "--header"]:
            i += 1
            h = parts[i]
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
        elif part in ["-d", "--data", "--data-raw"]:
            i += 1
            if method == "GET":
                method = "POST"
            try:
                body = json.loads(parts[i])
            except:
                pass
        i += 1
        
    if url:
        endpoints.append({
            "name": "Curl Request",
            "method": method,
            "url": url,
            "headers": headers,
            "body": body
        })
        
    return endpoints

# Note: openapi-core parsing could be added here for `parse_openapi` but for brevity we'll keep to Postman/Curl
# as those cover 99% of user "paste" flows.
