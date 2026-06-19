from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import tempfile
import os
import pandas as pd
from docling.document_converter import DocumentConverter
from unstructured.partition.auto import partition

app = FastAPI(title="QA RAG Extraction Service")

# Initialize Docling converter
doc_converter = DocumentConverter()

@app.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    """
    Extracts content from a file and converts it to Markdown.
    Supports PDF, DOCX, CSV, XLSX, TXT, MD, HTML.
    """
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        markdown_content = ""
        
        # Route based on file extension
        if ext in ["pdf", "docx", "doc"]:
            # Use Docling for rich documents (PDF/Word)
            result = doc_converter.convert(tmp_path)
            markdown_content = result.document.export_to_markdown()
            
        elif ext in ["csv", "xlsx", "xls"]:
            # Use Pandas for tabular data
            if ext == "csv":
                df = pd.read_csv(tmp_path)
            else:
                df = pd.read_excel(tmp_path)
            markdown_content = df.to_markdown(index=False)
            
        elif ext in ["txt", "md", "html", "htm"]:
            # Use Unstructured for raw text and HTML
            elements = partition(filename=tmp_path)
            markdown_content = "\n\n".join([str(el) for el in elements])
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
            
        return {
            "filename": filename,
            "markdown": markdown_content,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
        
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
