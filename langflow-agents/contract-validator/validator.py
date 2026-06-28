import json
import logging
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Union, Generator, Tuple
import concurrent.futures

def fetch_url_json(url: str) -> Any:
    """Fetches JSON content from a URL."""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            return json.loads(content)
    except Exception as e:
        raise ValueError(f"Failed to fetch JSON from URL '{url}': {str(e)}")

try:
    import jsonschema
    from jsonschema import Draft7Validator
    from jsonschema.exceptions import ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("JSONSchemaValidator")

class JSONSchemaValidator:
    def __init__(self, schema_source: Union[str, dict, Path]):
        """
        Initialize the validator with a schema.
        :param schema_source: JSON string of schema, schema dictionary, or path to schema file.
        """
        self.schema = self._load_json(schema_source)
        if JSONSCHEMA_AVAILABLE:
            try:
                # Validate the schema itself
                Draft7Validator.check_schema(self.schema)
                # Enable standard format checker (e.g. for validating formats like "email")
                self.validator = Draft7Validator(self.schema, format_checker=Draft7Validator.FORMAT_CHECKER)
            except Exception as e:
                raise ValueError(f"Invalid JSON Schema: {str(e)}")
        else:
            self.validator = None

    def _load_json(self, source: Union[str, dict, Path]) -> dict:
        if isinstance(source, dict):
            return source
        
        # Check if source is an HTTP/HTTPS URL
        if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
            return fetch_url_json(source)
        
        # Check if source is a file path
        if isinstance(source, Path) or (isinstance(source, str) and (source.endswith('.json') or Path(source).exists())):
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                raise ValueError(f"Failed to load JSON file from {source}: {str(e)}")
        
        # Check if source is raw JSON string
        if isinstance(source, str):
            try:
                return json.loads(source)
            except Exception as e:
                raise ValueError(f"Failed to parse JSON string: {str(e)}")
        
        raise TypeError("Invalid source type for JSON. Expected dict, path, or JSON string.")

    def validate_payload(self, payload: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a single JSON payload.
        Returns a tuple: (is_valid, list_of_errors)
        Where list_of_errors contains dictionaries with keys: 'path', 'message', 'rule', 'value'
        """
        if not JSONSCHEMA_AVAILABLE:
            return False, [{
                "path": "/",
                "message": "jsonschema package is not installed. Please run 'pip install jsonschema'.",
                "rule": "dependency_missing",
                "value": None
            }]

        errors = []
        try:
            # We use iter_errors to capture all validation errors
            validation_errors = sorted(self.validator.iter_errors(payload), key=lambda e: e.path)
            for err in validation_errors:
                # Represent path as a JSON Pointer (e.g. /users/0/name)
                path = "/" + "/".join(str(p) for p in err.relative_path)
                errors.append({
                    "path": path if path != "/" else "/",
                    "message": err.message,
                    "rule": err.validator,
                    "value": err.validator_value
                })
        except Exception as e:
            errors.append({
                "path": "/",
                "message": f"Unexpected error during validation: {str(e)}",
                "rule": "system_error",
                "value": None
            })

        return len(errors) == 0, errors

    def validate_batch(self, payloads: List[Tuple[str, Any]], max_workers: int = 4) -> Dict[str, Any]:
        """
        Validate a batch of payloads.
        :param payloads: List of tuples (identifier/source, payload_dict)
        :param max_workers: Maximum threads to use for parallel processing
        """
        results = {
            "summary": {
                "total": len(payloads),
                "passed": 0,
                "failed": 0,
                "errors": 0
            },
            "details": []
        }

        if not payloads:
            return results

        def _validate_task(identifier: str, payload: Any) -> Dict[str, Any]:
            # If payload has parser/load errors stored inside
            if isinstance(payload, dict) and "__error__" in payload:
                return {
                    "identifier": identifier,
                    "valid": False,
                    "errors": [{
                        "path": "/",
                        "message": payload["__error__"],
                        "rule": "load_error",
                        "value": None
                    }],
                    "status": "error"
                }

            try:
                is_valid, errors = self.validate_payload(payload)
                return {
                    "identifier": identifier,
                    "valid": is_valid,
                    "errors": errors,
                    "status": "success"
                }
            except Exception as e:
                return {
                    "identifier": identifier,
                    "valid": False,
                    "errors": [{
                        "path": "/",
                        "message": f"Payload parsing/processing failed: {str(e)}",
                        "rule": "processing_error",
                        "value": None
                    }],
                    "status": "error"
                }

        # Multi-threading for batch validation to improve processing times on larger list of files
        if max_workers > 1 and len(payloads) > 20:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_ident = {
                    executor.submit(_validate_task, ident, pay): ident for ident, pay in payloads
                }
                for future in concurrent.futures.as_completed(future_to_ident):
                    res = future.result()
                    self._process_task_result(res, results)
        else:
            for ident, pay in payloads:
                res = _validate_task(ident, pay)
                self._process_task_result(res, results)

        return results

    def _process_task_result(self, res: Dict[str, Any], results: Dict[str, Any]):
        results["details"].append(res)
        if res["status"] == "error":
            results["summary"]["errors"] += 1
            results["summary"]["failed"] += 1
        elif res["valid"]:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1

def load_payloads(source: Union[str, Path], unpack: bool = True) -> List[Tuple[str, Any]]:
    """
    Loads payloads from different formats:
    - Path to a directory containing .json files
    - Path to a single .json file (can be a JSON object, or a JSON array of objects)
    - Path to a single .jsonl (JSON Lines) file
    - Raw JSON string representing an object, array, or multiple lines of JSON
    - HTTP/HTTPS URL returning a JSON object or array
    """
    payloads = []
    
    # Check if source is a URL
    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
        try:
            data = fetch_url_json(source)
            if unpack and isinstance(data, list):
                for idx, item in enumerate(data):
                    payloads.append((f"URL [Index {idx}]", item))
            else:
                payloads.append(("URL", data))
            return payloads
        except Exception as e:
            return [("URL", {"__error__": f"URL Fetch Error: {str(e)}"})]

    path_obj = Path(source) if isinstance(source, (str, Path)) else None
    
    # 1. Directory of JSON files
    if path_obj and path_obj.is_dir():
        for file_path in sorted(path_obj.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    payloads.append((file_path.name, content))
            except Exception as e:
                payloads.append((file_path.name, {"__error__": f"JSON Load Error: {str(e)}"}))
        return payloads

    # 2. File Input
    if path_obj and path_obj.is_file():
        # JSON Lines file
        if path_obj.suffix.lower() == ".jsonl":
            try:
                with open(path_obj, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payloads.append((f"{path_obj.name} [Line {i}]", json.loads(line)))
                        except Exception as e:
                            payloads.append((f"{path_obj.name} [Line {i}]", {"__error__": f"Line parsing error: {str(e)}"}))
            except Exception as e:
                payloads.append((path_obj.name, {"__error__": f"JSONL Read Error: {str(e)}"}))
            return payloads
        
        # Single JSON file (could contain an array or a single object)
        try:
            with open(path_obj, "r", encoding="utf-8") as f:
                data = json.load(f)
                if unpack and isinstance(data, list):
                    for idx, item in enumerate(data):
                        payloads.append((f"{path_obj.name} [Index {idx}]", item))
                else:
                    payloads.append((path_obj.name, data))
        except Exception as e:
            payloads.append((path_obj.name, {"__error__": f"JSON Read Error: {str(e)}"}))
        return payloads

    # 3. Raw String (Chat input)
    if isinstance(source, str):
        content = source.strip()
        if not content:
            return payloads
            
        # Try as single JSON Object or Array
        try:
            data = json.loads(content)
            if unpack and isinstance(data, list):
                for idx, item in enumerate(data):
                    payloads.append((f"Raw String [Index {idx}]", item))
            else:
                payloads.append(("Raw String", data))
            return payloads
        except json.JSONDecodeError:
            pass

        # Try as JSON Lines (multiple lines where each is a JSON object)
        lines = content.splitlines()
        if len(lines) > 1:
            parsed_lines = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed_lines.append((f"Raw String [Line {i}]", json.loads(line)))
                except json.JSONDecodeError:
                    parsed_lines.append((f"Raw String [Line {i}]", {"__error__": f"JSON Decode Error on line {i}"}))
            return parsed_lines

        raise ValueError("Provided string could not be parsed as a JSON object, array, or JSON lines.")

    raise TypeError("Invalid source type. Expected a file path, directory path, or string content.")
