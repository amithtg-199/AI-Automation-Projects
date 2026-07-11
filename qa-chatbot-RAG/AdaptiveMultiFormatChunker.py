import os
import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, Output
from langflow.schema import Data

class AdaptiveMultiFormatChunker(Component):
    display_name = "Adaptive Multi-Format Chunker & Metadata Splitter"
    description = "Receives file data/content from Read File, extracts structured test case metadata (TID, Priority, Status, Module), and splits exactly 1 row = 1 atomic Document with project_name versioning."
    icon = "layers"

    inputs = [
        HandleInput(
            name="input_data",
            display_name="File Output (Connect Table or Message Pin)",
            input_types=["Table", "Message", "Data", "DataFrame", "str", "Any"],
            required=True,
            is_list=True
        ),
        StrInput(name="project_name", display_name="Project Name (Collection Name)", value="ecommerce_test_cases", required=True),
        StrInput(name="version_tag", display_name="Version Metadata Tag", value="v1", required=False),
    ]

    outputs = [
        Output(display_name="Output Documents", name="documents", method="build_chunks")
    ]

    def build_chunks(self) -> List[Data]:
        return self.build(
            input_data=getattr(self, "input_data", []),
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            version_tag=getattr(self, "version_tag", "v1"),
        )

    def build_config(self):
        return {
            "input_data": {"display_name": "File Output (Connect Table or Message Pin)", "field_type": "HandleInput", "input_types": ["Table", "Message", "Data", "DataFrame", "str", "Any"], "required": True},
            "project_name": {"display_name": "Project Name (Collection Name)", "field_type": "str", "required": True, "value": "ecommerce_test_cases"},
            "version_tag": {"display_name": "Version Metadata Tag", "field_type": "str", "value": "v1", "required": False},
        }

    def build(
        self,
        input_data: Union[List[Data], Data, List[Dict[str, Any]], str],
        project_name: str = "ecommerce_test_cases",
        version_tag: str = "v1",
    ) -> List[Data]:
        print(f"[INFO] Adaptive Chunker processing extraction & splitting for Project '{project_name}' (Version: {version_tag})...")

        # Parse numeric version_num from version_tag (e.g., "v2" -> 2)
        ver_num = 1
        if version_tag.startswith("v") and version_tag[1:].isdigit():
            ver_num = int(version_tag[1:])
        elif version_tag.isdigit():
            ver_num = int(version_tag)
            version_tag = f"v{ver_num}"

        base_metadata = {
            "project_name": project_name,
            "version": version_tag,
            "version_num": ver_num,
            "is_latest": True
        }

        documents: List[Data] = []

        # Helper to process a dictionary / row into an atomic Test Case Data chunk
        def _process_dict_row(row: Dict[str, Any], idx: int):
            tid = str(row.get("TID", row.get("tid", row.get("id", f"TC_{idx+1:04d}")))).strip()
            scenario = str(row.get("Scenario", row.get("scenario", "E-Commerce QA"))).strip()
            desc = str(row.get("Testcase Description", row.get("description", ""))).strip()
            priority = str(row.get("Priority", row.get("priority", "Medium"))).strip()
            status = str(row.get("Status", row.get("status", "Not Executed"))).strip()
            is_auto = str(row.get("Is Automated", row.get("is_automated", "No"))).strip()
            pre = str(row.get("Precondition", row.get("precondition", ""))).strip()
            steps = str(row.get("Test Steps", row.get("steps_to_execute", ""))).strip()
            expected = str(row.get("Expected Result", row.get("expected_result", ""))).strip()
            actual = str(row.get("Actual Result", row.get("actual_result", ""))).strip()
            comments = str(row.get("Misc. (Comments)", row.get("comments", ""))).strip()
            qa_name = str(row.get("Executed QA Name", row.get("qa_name", "QA"))).strip()

            meta = {
                **base_metadata,
                "source_type": "csv_test_case",
                "tid": tid,
                "scenario": scenario,
                "module": scenario.split(" - ")[0] if " - " in scenario else scenario,
                "priority": priority,
                "status": status,
                "is_automated": is_auto,
                "qa_name": qa_name,
            }

            content = (
                f"Test ID: {tid} | Scenario Category: {scenario}\n"
                f"Priority: {priority} | Automated: {is_auto} | Status: {status}\n"
                f"Description: {desc}\n"
                f"Precondition: {pre}\n"
                f"Test Steps: {steps}\n"
                f"Expected Result: {expected}\n"
                f"Actual Result: {actual}\n"
                f"QA Notes & A/B Testing: {comments}"
            )
            item = Data(data={"page_content": content, "text": content, **meta})
            setattr(item, "page_content", content)
            setattr(item, "metadata", meta)
            documents.append(item)

        # Helper to process raw CSV string text
        def _process_csv_string(csv_text: str):
            reader = csv.DictReader(io.StringIO(csv_text))
            for idx, row in enumerate(reader):
                _process_dict_row(row, idx)

        # Universal single-item processor for DataFrame, Message, Data, dict, or str
        def _process_single_item(item: Any, idx: int = 0):
            if item is None:
                return
            # 1. Check if DataFrame (pandas DataFrame or Table from Structured Content)
            if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")) and not isinstance(item, (Data, dict)):
                try:
                    records = item.to_dict(orient="records")
                    if isinstance(records, list):
                        for r_idx, row in enumerate(records):
                            if isinstance(row, dict):
                                _process_dict_row(row, r_idx)
                        return
                except Exception:
                    pass
            # 2. Check if dict directly
            if isinstance(item, dict):
                if any(k in item for k in ["TID", "tid", "Scenario", "Testcase Description"]):
                    _process_dict_row(item, idx)
                elif "text" in item and isinstance(item["text"], str) and ("TID" in item["text"] or "," in item["text"]):
                    _process_csv_string(item["text"])
                else:
                    _process_dict_row(item, idx)
                return
            # 3. Check if str directly
            if isinstance(item, str):
                if os.path.exists(item) and item.endswith(".csv"):
                    try:
                        with open(item, mode="r", encoding="utf-8", errors="ignore") as f:
                            _process_csv_string(f.read())
                        return
                    except Exception:
                        pass
                if "TID" in item and "Scenario" in item:
                    _process_csv_string(item)
                else:
                    meta = {**base_metadata, "source_type": "text_chunk", "chunk_index": idx}
                    d_item = Data(data={"page_content": item, "text": item, **meta})
                    setattr(d_item, "page_content", item)
                    setattr(d_item, "metadata", meta)
                    documents.append(d_item)
                return
            # 4. Check if object has .data dict or .model_dump() dict (covers Data, Message, Record, etc.)
            data_dict = None
            if hasattr(item, "data") and isinstance(getattr(item, "data"), dict):
                data_dict = getattr(item, "data")
            elif hasattr(item, "model_dump") and callable(getattr(item, "model_dump")):
                try:
                    data_dict = item.model_dump()
                except Exception:
                    pass

            if isinstance(data_dict, dict):
                if any(k in data_dict for k in ["TID", "tid", "Scenario", "Testcase Description"]):
                    _process_dict_row(data_dict, idx)
                    return
                elif "text" in data_dict and isinstance(data_dict["text"], str) and "TID" in data_dict["text"] and "Scenario" in data_dict["text"]:
                    _process_csv_string(data_dict["text"])
                    return
                elif "file_path" in data_dict and os.path.exists(str(data_dict["file_path"])):
                    with open(data_dict["file_path"], mode="r", encoding="utf-8", errors="ignore") as f:
                        _process_csv_string(f.read())
                    return

            # 5. Check if object has .text string (covers Message, Data, Document, etc.)
            if hasattr(item, "text") and isinstance(getattr(item, "text"), str) and getattr(item, "text"):
                raw_txt = getattr(item, "text")
                if "TID" in raw_txt and "Scenario" in raw_txt:
                    _process_csv_string(raw_txt)
                    return
                else:
                    meta = {**base_metadata, "source_type": "object_text", "chunk_index": idx}
                    d_item = Data(data={"page_content": raw_txt, "text": raw_txt, **meta})
                    setattr(d_item, "page_content", raw_txt)
                    setattr(d_item, "metadata", meta)
                    documents.append(d_item)
                    return

            # 6. Fallback string representation
            raw_str = str(item)
            if "TID" in raw_str and "Scenario" in raw_str:
                _process_csv_string(raw_str)
            else:
                meta = {**base_metadata, "source_type": "generic_data", "chunk_index": idx}
                d_item = Data(data={"page_content": raw_str, "text": raw_str, **meta})
                setattr(d_item, "page_content", raw_str)
                setattr(d_item, "metadata", meta)
                documents.append(d_item)

        # Run process loop over input_data
        if isinstance(input_data, list):
            for idx, itm in enumerate(input_data):
                _process_single_item(itm, idx)
        else:
            _process_single_item(input_data, 0)

        print(f"[SUCCESS] Adaptive Chunker generated {len(documents)} structured atomic Data chunks.")
        return documents
