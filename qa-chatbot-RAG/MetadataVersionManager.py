import os
from typing import Dict, Any, Optional

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output

class MetadataVersionManager(Component):
    display_name = "Metadata & Version Manager"
    description = "Queries Qdrant collection ({project_name}) to find the latest existing version, increments it (v1 -> v2), and outputs version metadata dict for enrichment."
    icon = "git-branch"

    inputs = [
        StrInput(name="project_name", display_name="Project Name (Collection Name)", value="ecommerce_test_cases", required=True),
        StrInput(name="qdrant_url", display_name="Qdrant Server URL", value="http://qdrant:6333"),
        SecretStrInput(name="qdrant_api_key", display_name="Qdrant API Key", required=False),
    ]

    outputs = [
        Output(display_name="Version Metadata Dict", name="version_metadata", method="build_version")
    ]

    def build_version(self) -> Dict[str, Any]:
        return self.build(
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            qdrant_url=getattr(self, "qdrant_url", "http://localhost:6333"),
            qdrant_api_key=getattr(self, "qdrant_api_key", None),
        )

    def build_config(self):
        return {
            "project_name": {"display_name": "Project Name (Collection Name)", "field_type": "str", "required": True, "value": "ecommerce_test_cases"},
            "qdrant_url": {"display_name": "Qdrant Server URL", "field_type": "str", "value": "http://qdrant:6333"},
            "qdrant_api_key": {"display_name": "Qdrant API Key", "field_type": "str", "password": True, "required": False},
        }

    def build(
        self,
        project_name: str,
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        print(f"[INFO] MetadataVersionManager querying Qdrant ({qdrant_url}) for Project '{project_name}'...")
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None)
            
            # Check if collection exists
            collections = [c.name for c in client.get_collections().collections]
            if project_name not in collections:
                print(f"[INFO] Collection '{project_name}' not found. Assigning initial version: v1")
                return {
                    "project_name": project_name,
                    "version": "v1",
                    "version_num": 1,
                    "is_latest": True
                }
            
            # Scroll through existing records to find max version_num
            max_ver = 0
            offset = None
            while True:
                records, offset = client.scroll(
                    collection_name=project_name,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset
                )
                for r in records:
                    v_num = r.payload.get("version_num")
                    if isinstance(v_num, (int, float)) and v_num > max_ver:
                        max_ver = int(v_num)
                    elif isinstance(r.payload.get("version"), str) and r.payload["version"].startswith("v"):
                        try:
                            v_num_str = int(r.payload["version"][1:])
                            if v_num_str > max_ver:
                                max_ver = v_num_str
                        except ValueError:
                            pass
                if not offset:
                    break
            
            next_num = max_ver + 1
            print(f"[INFO] Found max existing version_num={max_ver}. Assigning new version: v{next_num}")
            return {
                "project_name": project_name,
                "version": f"v{next_num}",
                "version_num": next_num,
                "is_latest": True
            }
        except Exception as e:
            print(f"[WARN] Error querying Qdrant ({e}). Defaulting to v1.")
            return {
                "project_name": project_name,
                "version": "v1",
                "version_num": 1,
                "is_latest": True
            }

if __name__ == "__main__":
    mgr = MetadataVersionManager()
    res = mgr.build(project_name="ecommerce_test_cases")
    print("Version Metadata Result:", res)
