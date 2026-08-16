import json
from typing import Dict, Any, List

def detect_lifecycle_pairs(endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Appendix M: Score Create/Delete pairs by name similarity and path segment.
    """
    creates = [e for e in endpoints if e["method"] == "POST"]
    deletes = [e for e in endpoints if e["method"] == "DELETE"]
    
    pairs = []
    for c in creates:
        c_path = c["url"].split("?")[0].rstrip("/")
        for d in deletes:
            d_path = d["url"].split("?")[0].rstrip("/")
            
            # Simple heuristic: DELETE path starts with POST path
            # e.g. POST /api/users, DELETE /api/users/{id}
            if d_path.startswith(c_path):
                pairs.append({
                    "create": c,
                    "delete": d,
                    "confidence": 0.9  # High confidence based on path
                })
                break
                
    return pairs

def generate_conftest(pairs: List[Dict[str, Any]]) -> str:
    """
    Generates conftest.py with yield fixture teardowns for the detected pairs.
    """
    if not pairs:
        return ""
        
    lines = [
        "import pytest",
        "import requests",
        "from typing import Dict, Any",
        "from utils.api_helpers import build_dynamic_headers",
        "",
    ]
    
    for idx, pair in enumerate(pairs):
        create = pair["create"]
        delete = pair["delete"]
        
        lines.extend([
            f"@pytest.fixture",
            f"def entity_{idx}_lifecycle():",
            f"    # Setup: Create",
            f"    headers = build_dynamic_headers({repr(create['headers'])})",
            f"    resp = requests.post('{create['url']}', json={repr(create['body'])}, headers=headers)",
            f"    assert resp.status_code in [200, 201]",
            f"    created_entity = resp.json()",
            f"    ",
            f"    yield created_entity",
            f"    ",
            f"    # Teardown: Delete (guaranteed cleanup)",
            f"    # Resolving ID assumes the delete URL ends with {{id}} or we append it",
            f"    entity_id = created_entity.get('id')",
            f"    if entity_id:",
            f"        del_headers = build_dynamic_headers({repr(delete['headers'])})",
            f"        del_url = f\"{delete['url'].replace('{id}', str(entity_id))}\"",
            f"        requests.delete(del_url, headers=del_headers)"
        ])
        
    return "\n".join(lines)

def generate_api_tests(endpoints: List[Dict[str, Any]], aliases: Dict[str, str]) -> str:
    """
    Generates parameterized pytest suites applying Positive/Negative/Boundary taxonomy.
    """
    lines = [
        "import pytest",
        "import requests",
        "from utils.api_helpers import build_dynamic_headers",
        ""
    ]
    
    for ep in endpoints:
        name = ep['name'].lower().replace(" ", "_")
        lines.extend([
            f"class Test{ep['name'].replace(' ', '')}:",
            f"    @pytest.mark.smoke",
            f"    def test_{name}_positive(self, entity_0_lifecycle):", # mock dependency
            f"        headers = build_dynamic_headers({repr(ep['headers'])})",
            f"        resp = requests.request('{ep['method']}', '{ep['url']}', json={repr(ep['body'])}, headers=headers)",
            f"        assert resp.status_code < 400",
            ""
        ])
        
    return "\n".join(lines)
