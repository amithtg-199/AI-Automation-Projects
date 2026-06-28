import sys
import json
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Union, Tuple

from langflow.custom import Component
from langflow.inputs import MultilineInput, IntInput
from langflow.io import Output
from langflow.schema.message import Message

class JSONSchemaValidatorComponent(Component):
    display_name = "JSON Schema Validator"
    description = (
        "Validates JSON payloads (raw JSON, JSON Lines, folder of JSONs, or file paths) "
        "against a given JSON Schema. Scales to handle 100s of payloads."
    )
    icon = "check-square"

    # Inputs definition for newer Langflow versions
    inputs = [
        MultilineInput(
            name="schema_input",
            display_name="JSON Schema",
            info="Raw JSON schema or path to a schema file (.json) or URL.",
            value="",
            required=True,
        ),
        MultilineInput(
            name="payload_input",
            display_name="JSON Payload(s)",
            info="Raw JSON payload, JSON Lines (jsonl), path to file, path to directory, or URL.",
            value="",
            required=True,
        ),
        IntInput(
            name="workers",
            display_name="Parallel Workers",
            info="Number of threads for batch validation.",
            value=4,
            advanced=True,
        ),
    ]

    # Outputs definition for newer Langflow versions
    outputs = [
        Output(name="report", display_name="Markdown Report", method="build_report"),
        Output(name="results_json", display_name="JSON Results", method="build_json"),
        Output(name="is_valid", display_name="Is Valid", method="build_status"),
    ]

    def build_config(self) -> Dict[str, Any]:
        """Backward compatibility configuration dictionary for older Langflow versions."""
        return {
            "schema_input": {
                "display_name": "JSON Schema",
                "info": "Raw JSON schema or path to a schema file (.json) or URL.",
                "field_type": "str",
                "multiline": True,
            },
            "payload_input": {
                "display_name": "JSON Payload(s)",
                "info": "Raw JSON payload, JSON Lines (jsonl), path to file, path to directory, or URL.",
                "field_type": "str",
                "multiline": True,
            },
            "workers": {
                "display_name": "Parallel Workers",
                "info": "Number of threads for batch validation.",
                "field_type": "int",
                "value": 4,
                "advanced": True,
            },
        }

    # ==========================================
    # Helper Methods (Encapsulated)
    # ==========================================

    def fetch_url_json(self, url: str) -> Any:
        """Fetches JSON content from a URL."""
        import urllib.request
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

    def load_json(self, source: Union[str, dict, Path]) -> dict:
        """Loads a JSON object from a dictionary, path, URL, or raw string."""
        if isinstance(source, dict):
            return source
        
        # Check if source is an HTTP/HTTPS URL
        if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
            return self.fetch_url_json(source)
        
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

    def load_payloads(self, source: Union[str, Path], unpack: bool = True) -> List[Tuple[str, Any]]:
        """Loads payloads from URLs, directories, single files, JSONL, or raw text."""
        payloads = []
        
        # Check if source is a URL
        if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
            try:
                data = self.fetch_url_json(source)
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

            # Try as JSON Lines
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

    def validate_payload(self, schema: dict, payload: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        """Validates a single payload against the schema."""
        try:
            import jsonschema
            from jsonschema import Draft7Validator
            jsonschema_available = True
        except ImportError:
            jsonschema_available = False

        if not jsonschema_available:
            return False, [{
                "path": "/",
                "message": "jsonschema package is not installed on the Langflow server. Please run 'pip install jsonschema'.",
                "rule": "dependency_missing",
                "value": None
            }]

        errors = []
        try:
            Draft7Validator.check_schema(schema)
            validator = Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER)
            validation_errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
            for err in validation_errors:
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

    def validate_batch(self, schema: dict, payloads: List[Tuple[str, Any]], max_workers: int = 4) -> Dict[str, Any]:
        """Validates a batch of payloads using thread workers."""
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
                is_valid, errors = self.validate_payload(schema, payload)
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

        # Multi-threading for batch validation
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

    def _execute_validation(self, schema_input: str, payload_input: str, workers: int) -> Dict[str, Any]:
        """Runs the validation logic and returns the full results dictionary."""
        # Check if the payload_input alone (or identical inputs) is a combined schema and payload structure
        is_combined = False
        schema_data = schema_input
        payload_data = payload_input

        if payload_input:
            try:
                parsed_combined = json.loads(payload_input.strip())
                if isinstance(parsed_combined, dict) and "schema" in parsed_combined and ("payload" in parsed_combined or "payloads" in parsed_combined):
                    is_combined = True
                    schema_data = parsed_combined["schema"]
                    payload_data = parsed_combined.get("payload") or parsed_combined.get("payloads")
            except Exception:
                pass

        # If it's not combined and either input is missing, return error
        if not is_combined and (not schema_input or not payload_input):
            return {
                "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1},
                "details": [{
                    "identifier": "Validator",
                    "valid": False,
                    "errors": [{"path": "/", "message": "Schema input or payload input is empty.", "rule": "missing_inputs", "value": None}],
                    "status": "error"
                }]
            }

        # Load and validate JSON Schema
        try:
            schema_dict = self.load_json(schema_data)
        except Exception as e:
            return {
                "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1},
                "details": [{
                    "identifier": "Schema Loader",
                    "valid": False,
                    "errors": [{"path": "/", "message": f"Failed to load or parse Schema: {e}", "rule": "schema_error", "value": None}],
                    "status": "error"
                }]
            }

        # Load Payloads
        try:
            # If the schema type is explicitly 'array', we should validate the payload as a whole array (no unpacking)
            unpack = (schema_dict.get("type") != "array")
            
            if is_combined:
                if unpack and isinstance(payload_data, list):
                    payloads = [(f"Payload {idx}", item) for idx, item in enumerate(payload_data)]
                elif isinstance(payload_data, dict) or isinstance(payload_data, list):
                    payloads = [("Payload", payload_data)]
                else:
                    payloads = self.load_payloads(payload_data, unpack=unpack)
            else:
                payloads = self.load_payloads(payload_data, unpack=unpack)
        except Exception as e:
            return {
                "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1},
                "details": [{
                    "identifier": "Payload Loader",
                    "valid": False,
                    "errors": [{"path": "/", "message": f"Failed to load or parse payloads: {e}", "rule": "payload_error", "value": None}],
                    "status": "error"
                }]
            }

        if not payloads:
            return {
                "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 1},
                "details": [{
                    "identifier": "Payload Loader",
                    "valid": False,
                    "errors": [{"path": "/", "message": "No payloads could be loaded from input.", "rule": "empty_payloads", "value": None}],
                    "status": "error"
                }]
            }

        return self.validate_batch(schema_dict, payloads, max_workers=workers)

    def _generate_markdown(self, results: Dict[str, Any]) -> str:
        """Helper to generate a clean markdown summary report."""
        summary = results["summary"]
        details = sorted(results["details"], key=lambda x: x["identifier"])
        
        md = []
        md.append("### 📝 Contract Validation Report")
        md.append(f"**Total Payloads**: {summary['total']} | **Passed ✅**: {summary['passed']} | **Failed ❌**: {summary['failed']}")
        if summary.get('errors', 0) > 0:
            md.append(f"**Errors ⚠️**: {summary['errors']}")
        
        md.append("\n| Payload Name / Source | Status | Errors / Details |")
        md.append("| :--- | :--- | :--- |")
        
        for item in details:
            name = item["identifier"]
            if item["valid"]:
                status = "✅ PASSED"
                details_str = "No issues found."
            else:
                status = "❌ FAILED"
                err_details = []
                for err in item["errors"]:
                    path_prefix = f"`{err['path']}`: " if err['path'] and err['path'] != "/" else ""
                    err_details.append(f"{path_prefix}{err['message']}")
                details_str = "<br>".join(err_details)
            md.append(f"| {name} | {status} | {details_str} |")
            
        return "\n".join(md)

    # Output methods for newer Langflow versions
    def build_report(self) -> Message:
        results = self._execute_validation(self.schema_input, self.payload_input, self.workers)
        report_text = self._generate_markdown(results)
        return Message(text=report_text)

    def build_json(self) -> Dict[str, Any]:
        return self._execute_validation(self.schema_input, self.payload_input, self.workers)

    def build_status(self) -> bool:
        results = self._execute_validation(self.schema_input, self.payload_input, self.workers)
        return results["summary"]["failed"] == 0

    # Fallback build method for older Langflow versions or general flow builders
    def build(self, schema_input: str, payload_input: str, workers: int = 4) -> Dict[str, Any]:
        results = self._execute_validation(schema_input, payload_input, workers)
        markdown_report = self._generate_markdown(results)
        
        return {
            "is_valid": results["summary"]["failed"] == 0,
            "report": markdown_report,
            "results_json": results
        }
