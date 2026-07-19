# Input Data Sources for Ingestion

This directory is where you will place your raw data files before triggering the ingestion pipeline.

As specified in the architecture, you should create a folder for each of your projects here.

## Directory Structure Example:

```text
backend/input_data/
├── My_QA_Project/
│   ├── selenium_framework/         # Clone your Selenium repo here
│   ├── playwright_framework/       # Clone your Playwright repo here
│   ├── testdata.csv                # Test cases
│   ├── BRD_v1.pdf                  # Product requirement docs
│   └── architecture_diagram.txt    # Lucid chart exports
└── Another_Project/
    ├── ...
```

## Supported Formats
The ingestion pipeline will be configured to parse:
- `.pdf` (via Unstructured.io/LlamaParse)
- `.docx`
- `.txt` (Meeting notes, Lucid chart exports)
- `.csv` / `.xlsx` (Test cases)
- Raw code files (`.py`, `.java`, `.ts`) via AST parsing.

Once you have placed your files in a project folder here, you will be able to select that project from the frontend UI and click **Start Ingestion** to process them into Qdrant and Neo4j.
