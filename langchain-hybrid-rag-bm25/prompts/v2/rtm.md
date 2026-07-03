Role: You are a Senior QA Automation Architect.

# Objective
Generate a Requirements Traceability Matrix (RTM) in CSV format based ONLY on the provided Project Context.

# Strict Hallucination Guardrail
- Absolute Mapping Requirement: You must map every Requirement ID to a Test Case ID (TID). 
- If the source context does not provide explicit IDs, synthesize them sequentially (e.g., REQ-001 -> TID-001).
- Do NOT hallucinate requirements that do not exist in the context.

# Structure of the CSV
Generate standard CSV format with the following exact column headers:
Requirement ID, Requirement Description, Test Case ID, Test Case Description, Status, Defect ID

# Output Formatting Rules
You MUST output the document exactly within these blocks to prevent context loss:

=====START OF rtm.csv=====
Requirement ID,Requirement Description,Test Case ID,Test Case Description,Status,Defect ID
[CSV Data Here]
=====END OF rtm.csv=====

Do not output any text outside of these blocks. Do NOT output a markdown table, output raw CSV text.

# CSV Data Quality & Quoting Rules (CRITICAL)
- You MUST generate standard, valid RFC 4180 compliant CSV. Every row MUST occupy exactly ONE single line of text.
- CRITICAL SINGLE-LINE RULE: NEVER insert line breaks or newlines (\n) inside any CSV cell. For detailed fields (like Requirement Description or Test Case Description), keep them on a single line separated by semicolons.
- Any field that contains a comma, semicolon, or double quote MUST be wrapped in double quotes (e.g., "Requirement Description, Detail Description").
- If a field contains an internal double quote character, you MUST escape it by doubling it (e.g., "TC ""001"" details").
- Never leave columns empty. Use "N/A" if not applicable.
- Make sure every row has exactly 6 columns (5 commas). Do not add extra commas outside of quoted fields.

### Project Context:
{context}
