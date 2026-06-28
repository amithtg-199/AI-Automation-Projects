import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Prevent UnicodeEncodeError on Windows console when printing emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from validator import JSONSchemaValidator, load_payloads, JSONSCHEMA_AVAILABLE

def print_ascii_table(headers: List[str], rows: List[List[Any]]):
    """Prints a formatted ASCII table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            widths[idx] = max(widths[idx], len(str(val)))
            
    format_str = " | ".join(f"{{:<{w}}}" for w in widths)
    separator = "-+-".join("-" * w for w in widths)
    
    print(format_str.format(*headers))
    print(separator)
    for row in rows:
        print(format_str.format(*[str(val) for val in row]))

def generate_markdown_report(schema_path: str, summary: Dict[str, int], details: List[Dict[str, Any]]) -> str:
    """Generates a clean Markdown report of the validation results."""
    md = []
    md.append("# 📝 Contract Validation Report")
    md.append(f"\n* **Schema Reference**: `{schema_path}`")
    md.append("\n## 📊 Summary")
    md.append(f"- **Total Payloads**: {summary['total']}")
    md.append(f"- **Passed ✅**: {summary['passed']}")
    md.append(f"- **Failed ❌**: {summary['failed']}")
    if summary['errors'] > 0:
        md.append(f"- **System/Load Errors ⚠️**: {summary['errors']}")

    md.append("\n## 🔍 Details")
    md.append("| Payload / File | Status | Errors / Details |")
    md.append("| :--- | :--- | :--- |")
    
    for item in details:
        name = item["identifier"]
        if item["valid"]:
            status = "✅ PASSED"
            details_str = "No issues found"
        else:
            status = "❌ FAILED"
            err_details = []
            for err in item["errors"]:
                path_prefix = f"`{err['path']}`: " if err['path'] else ""
                err_details.append(f"{path_prefix}{err['message']}")
            details_str = "<br>".join(err_details)
        md.append(f"| {name} | {status} | {details_str} |")
        
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(
        description="JSON Schema Batch Validator CLI - Validate hundreds of payloads against a contract schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  python cli.py --schema user_schema.json --input payload.json

  # Validate a folder of JSON files
  python cli.py --schema user_schema.json --input ./payloads_folder/

  # Validate a JSON Lines file
  python cli.py --schema user_schema.json --input payloads.jsonl --format table

  # Save validation report as Markdown
  python cli.py --schema user_schema.json --input payloads.jsonl --format markdown --output report.md
"""
    )
    parser.add_argument("-s", "--schema", required=True, help="Path to the JSON schema file or raw JSON schema string.")
    parser.add_argument("-i", "--input", required=True, help="Path to a JSON file, directory of JSON files, JSONL file, or raw JSON string.")
    parser.add_argument("-f", "--format", choices=["table", "json", "markdown"], default="table", help="Output format for the CLI (default: table).")
    parser.add_argument("-o", "--output", help="Optional path to save the output report.")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Number of concurrent workers for batch processing (default: 4).")

    args = parser.parse_args()

    # Prerequisite check
    if not JSONSCHEMA_AVAILABLE:
        print("⚠️ Warning: Python 'jsonschema' library is not installed. Validations will fail.", file=sys.stderr)
        print("Please run: pip install jsonschema", file=sys.stderr)
        sys.exit(1)

    try:
        # Load schema
        validator = JSONSchemaValidator(args.schema)
    except Exception as e:
        print(f"❌ Error loading schema: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Determine if we should unpack payloads based on schema type
        unpack = (validator.schema.get("type") != "array")
        # Load payloads
        payloads = load_payloads(args.input, unpack=unpack)
    except Exception as e:
        print(f"❌ Error loading payloads: {e}", file=sys.stderr)
        sys.exit(1)

    if not payloads:
        print("⚠️ No payloads found or loaded from the input source.", file=sys.stderr)
        sys.exit(0)

    # Validate
    results = validator.validate_batch(payloads, max_workers=args.workers)
    summary = results["summary"]
    details = sorted(results["details"], key=lambda x: x["identifier"])

    # Output formatting
    report_content = ""
    if args.format == "json":
        report_content = json.dumps(results, indent=2)
        print(report_content)
    elif args.format == "markdown":
        report_content = generate_markdown_report(args.schema, summary, details)
        print(report_content)
    else:  # table
        print(f"\n=== VALIDATION SUMMARY ===")
        print(f"Total Payloads: {summary['total']}")
        print(f"Passed:         {summary['passed']} ✅")
        print(f"Failed:         {summary['failed']} ❌")
        if summary['errors'] > 0:
            print(f"Errors:         {summary['errors']} ⚠️")
        print("==========================\n")

        headers = ["Payload Identifier", "Status", "Errors Count", "Primary Error / Path"]
        rows = []
        for item in details:
            ident = item["identifier"]
            status = "PASSED" if item["valid"] else "FAILED"
            err_count = len(item["errors"])
            primary_err = "-"
            if err_count > 0:
                err = item["errors"][0]
                primary_err = f"[{err['path']}] {err['message']}"
                if len(item["errors"]) > 1:
                    primary_err += f" (+{len(item['errors']) - 1} more)"
            rows.append([ident, status, err_count, primary_err])
        
        print_ascii_table(headers, rows)

    # Save to file if output path is specified
    if args.output:
        try:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if args.format == "table":
                # For file output of tables, we format as text
                # We save markdown or json if specified, otherwise raw text
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(f"Validation Summary:\nTotal: {summary['total']}\nPassed: {summary['passed']}\nFailed: {summary['failed']}\nErrors: {summary['errors']}\n\n")
                    # simple table text
                    widths = [len(h) for h in headers]
                    for r in rows:
                        for idx, val in enumerate(r):
                            widths[idx] = max(widths[idx], len(str(val)))
                    format_str = " | ".join(f"{{:<{w}}}" for w in widths)
                    f.write(format_str.format(*headers) + "\n")
                    f.write("-+-".join("-" * w for w in widths) + "\n")
                    for r in rows:
                        f.write(format_str.format(*[str(val) for val in r]) + "\n")
            elif args.format == "markdown":
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(report_content)
            else:  # json
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
            print(f"\n💾 Report successfully saved to: {out_path.absolute()}")
        except Exception as e:
            print(f"❌ Failed to save report to file: {e}", file=sys.stderr)

    # Return non-zero code if any failed
    if summary["failed"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
