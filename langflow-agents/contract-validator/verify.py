import json
import sys
import time
from pathlib import Path

# Prevent UnicodeEncodeError on Windows console when printing emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from validator import JSONSchemaValidator, load_payloads

def create_sample_files() -> Tuple[Path, Path, Path]:
    """Generates sample schema and payloads for verification."""
    base_dir = Path(__file__).parent / "test_data"
    base_dir.mkdir(exist_ok=True)
    
    # 1. Standard JSON Schema for a User Profile
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "UserProfile",
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "minimum": 1
            },
            "name": {
                "type": "string",
                "minLength": 2
            },
            "email": {
                "type": "string",
                "format": "email"
            },
            "age": {
                "type": "integer",
                "minimum": 18,
                "maximum": 120
            },
            "tags": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "uniqueItems": True
            }
        },
        "required": ["id", "name", "email"]
    }
    
    schema_path = base_dir / "user_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    # 2. Generate 150 payloads: 140 valid, 10 invalid
    payloads_dir = base_dir / "payloads"
    payloads_dir.mkdir(exist_ok=True)
    
    # Clear existing if any
    for f in payloads_dir.glob("*.json"):
        f.unlink()

    # Valid payloads
    for i in range(1, 141):
        payload = {
            "id": i,
            "name": f"User Name {i}",
            "email": f"user{i}@example.com",
            "age": 20 + (i % 50),
            "tags": ["active", f"group-{i % 5}"]
        }
        with open(payloads_dir / f"payload_valid_{i:03d}.json", "w", encoding="utf-8") as f:
            json.dump(payload, f)

    # Invalid payloads (we'll capture specific expectations)
    invalid_cases = [
        # Case 1: Missing ID
        {"name": "No ID", "email": "noid@example.com", "age": 25},
        # Case 2: ID less than 1
        {"id": 0, "name": "Zero ID", "email": "zeroid@example.com", "age": 25},
        # Case 3: Name too short
        {"id": 143, "name": "A", "email": "shortname@example.com", "age": 25},
        # Case 4: Invalid email format (Note: default format checker in Draft7 requires package optional features, but standard jsonschema type checking will be done)
        {"id": 144, "name": "Bad Email", "email": "not-an-email", "age": 25},
        # Case 5: Age too young
        {"id": 145, "name": "Too Young", "email": "young@example.com", "age": 17},
        # Case 6: Age too old
        {"id": 146, "name": "Too Old", "email": "old@example.com", "age": 150},
        # Case 7: Duplicate tags
        {"id": 147, "name": "Duplicate Tags", "email": "dup@example.com", "age": 30, "tags": ["admin", "admin"]},
        # Case 8: Wrong tags item type
        {"id": 148, "name": "Wrong Tags Type", "email": "wtt@example.com", "age": 30, "tags": [123, "admin"]},
        # Case 9: Missing name
        {"id": 149, "email": "noname@example.com", "age": 30},
        # Case 10: Age wrong type
        {"id": 150, "name": "Wrong Age Type", "email": "wat@example.com", "age": "thirty"}
    ]

    for idx, case in enumerate(invalid_cases, 1):
        with open(payloads_dir / f"payload_invalid_{idx:02d}.json", "w", encoding="utf-8") as f:
            json.dump(case, f)

    # 3. Create a JSONL file containing all of them as well
    jsonl_path = base_dir / "all_payloads.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        # Write valid ones
        for i in range(1, 141):
            payload = {
                "id": i,
                "name": f"User Name {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "tags": ["active", f"group-{i % 5}"]
            }
            f.write(json.dumps(payload) + "\n")
        # Write invalid ones
        for case in invalid_cases:
            f.write(json.dumps(case) + "\n")

    return schema_path, payloads_dir, jsonl_path

def run_verification():
    print("🚀 Generating test schema and 150 payloads...")
    schema_path, payloads_dir, jsonl_path = create_sample_files()
    print("✅ Sample files generated in:")
    print(f"   Schema: {schema_path.relative_to(schema_path.parent.parent.parent)}")
    print(f"   Payloads directory: {payloads_dir.relative_to(payloads_dir.parent.parent.parent)}")
    print(f"   JSONL file: {jsonl_path.relative_to(jsonl_path.parent.parent.parent)}")

    print("\n📦 Initializing JSONSchemaValidator...")
    validator = JSONSchemaValidator(schema_path)

    # Test 1: Load from Directory
    print("\n--- Test 1: Validating Directory of Individual Files ---")
    start_time = time.perf_counter()
    dir_payloads = load_payloads(payloads_dir)
    load_time = time.perf_counter() - start_time
    print(f"Loaded {len(dir_payloads)} files in {load_time:.4f} seconds.")

    start_time = time.perf_counter()
    dir_results = validator.validate_batch(dir_payloads, max_workers=4)
    val_time = time.perf_counter() - start_time
    print(f"Validated {len(dir_payloads)} payloads in {val_time:.4f} seconds.")
    print(f"Passed: {dir_results['summary']['passed']}")
    print(f"Failed: {dir_results['summary']['failed']}")
    print(f"Errors: {dir_results['summary']['errors']}")

    # Asserts for verification
    assert len(dir_payloads) == 150, f"Expected 150 payloads, got {len(dir_payloads)}"
    assert dir_results['summary']['passed'] == 140, f"Expected 140 passed payloads, got {dir_results['summary']['passed']}"
    assert dir_results['summary']['failed'] == 10, f"Expected 10 failed payloads, got {dir_results['summary']['failed']}"
    print("✅ Test 1 Assertion Passed!")

    # Test 2: Load from JSONL file
    print("\n--- Test 2: Validating a single JSONL file ---")
    start_time = time.perf_counter()
    jsonl_payloads = load_payloads(jsonl_path)
    load_time = time.perf_counter() - start_time
    print(f"Loaded {len(jsonl_payloads)} lines from JSONL in {load_time:.4f} seconds.")

    start_time = time.perf_counter()
    jsonl_results = validator.validate_batch(jsonl_payloads, max_workers=4)
    val_time = time.perf_counter() - start_time
    print(f"Validated {len(jsonl_payloads)} payloads in {val_time:.4f} seconds.")
    print(f"Passed: {jsonl_results['summary']['passed']}")
    print(f"Failed: {jsonl_results['summary']['failed']}")
    print(f"Errors: {jsonl_results['summary']['errors']}")

    assert len(jsonl_payloads) == 150, f"Expected 150 payloads, got {len(jsonl_payloads)}"
    assert jsonl_results['summary']['passed'] == 140, f"Expected 140 passed payloads, got {jsonl_results['summary']['passed']}"
    assert jsonl_results['summary']['failed'] == 10, f"Expected 10 failed payloads, got {jsonl_results['summary']['failed']}"
    print("✅ Test 2 Assertion Passed!")

    # Test 3: Validate detailed error reporting
    print("\n--- Test 3: Verifying error reporting detail accuracy ---")
    # Let's inspect a few invalid ones
    invalid_results = [r for r in dir_results["details"] if not r["valid"]]
    
    # Check that we have details on why it failed
    for r in invalid_results[:3]:
        print(f"Payload: {r['identifier']}")
        for err in r["errors"]:
            print(f"   Path: '{err['path']}' | Rule: '{err['rule']}' | Message: '{err['message']}'")
            
    print("✅ Test 3 Verification Complete!")
    print("\n🎉 All verifications passed successfully!")

if __name__ == "__main__":
    from typing import Tuple
    run_verification()
