import os
import re
import json
from typing import List, Dict, Any, Optional

from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, IntInput, Output
from langflow.schema import Data

class AdaptiveQdrantHybridRetriever(Component):
    display_name = "Adaptive Qdrant Hybrid Retriever (With Confidence Guardrails)"
    description = "Intelligently routes between exact scroll and semantic Top-K search. Calculates exact Cosine similarity confidence scores and enforces version=latest pre-filtering."
    icon = "shield-check"

    inputs = [
        HandleInput(
            name="user_query",
            display_name="User Query / Question (Connect Chat Input)",
            input_types=["Message", "str", "Any"],
            required=True
        ),
        HandleInput(
            name="intent_dict",
            display_name="Intent Dict (Connect Query Intent Router)",
            input_types=["Data", "dict", "str", "Any"],
            required=False
        ),
        HandleInput(
            name="qdrant_node_results",
            display_name="Qdrant Node Results (Connect Qdrant Block)",
            input_types=["Data", "VectorStore", "Any"],
            required=False
        ),
        StrInput(name="project_name", display_name="Project Name (Collection Name)", value="ecommerce_test_cases", required=True),
        StrInput(name="qdrant_url", display_name="Qdrant Server URL", value="http://qdrant:6333"),
        SecretStrInput(name="qdrant_api_key", display_name="Qdrant API Key", required=False),
        SecretStrInput(name="mistral_api_key", display_name="Mistral API Key", required=False),
        IntInput(name="top_k", display_name="Semantic Top-K (for Mode B)", value=15),
    ]

    outputs = [
        Output(display_name="Retrieved Docs", name="retrieved_data", method="build_retrieval")
    ]

    def build_retrieval(self) -> List[Data]:
        return self.build(
            user_query=getattr(self, "user_query", ""),
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            qdrant_url=getattr(self, "qdrant_url", "http://qdrant:6333"),
            qdrant_api_key=getattr(self, "qdrant_api_key", None),
            mistral_api_key=getattr(self, "mistral_api_key", None),
            top_k=getattr(self, "top_k", 15),
            intent_dict=getattr(self, "intent_dict", None),
            qdrant_node_results=getattr(self, "qdrant_node_results", None),
        )

    def build_config(self):
        return {
            "user_query": {"display_name": "User Query / Question (Connect Chat Input)", "field_type": "HandleInput", "input_types": ["Message", "str", "Any"], "required": True},
            "intent_dict": {"display_name": "Intent Dict (Connect Query Intent Router)", "field_type": "HandleInput", "input_types": ["Data", "dict", "str", "Any"], "required": False},
            "qdrant_node_results": {"display_name": "Qdrant Node Results (Connect Qdrant Block)", "field_type": "HandleInput", "input_types": ["Data", "VectorStore", "Any"], "required": False},
            "project_name": {"display_name": "Project Name (Collection Name)", "field_type": "str", "required": True, "value": "ecommerce_test_cases"},
            "qdrant_url": {"display_name": "Qdrant Server URL", "field_type": "str", "value": "http://qdrant:6333"},
            "qdrant_api_key": {"display_name": "Qdrant API Key", "field_type": "str", "password": True, "required": False},
            "mistral_api_key": {"display_name": "Mistral API Key", "field_type": "str", "password": True, "required": False},
            "top_k": {"display_name": "Semantic Top-K (for Mode B)", "field_type": "int", "value": 15},
        }

    def _detect_payload_prefix(self, client: Any, project_name: str) -> str:
        """Detects whether point payload stores fields at top-level or nested inside payload.metadata.*"""
        try:
            records, _ = client.scroll(collection_name=project_name, limit=1, with_payload=True, with_vectors=False)
            if records and records[0].payload:
                p = records[0].payload
                if "metadata" in p and isinstance(p["metadata"], dict) and any(k in p["metadata"] for k in ["module", "status", "priority", "tid", "version_num", "scenario"]):
                    if not any(k in p for k in ["module", "status", "priority", "tid", "version_num", "scenario"]):
                        return "metadata."
        except Exception:
            pass
        return ""

    def _get_latest_version_num(self, client: Any, project_name: str) -> tuple[int, str]:
        """Finds the active latest version in Qdrant for this project."""
        try:
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
                    p = r.payload or {}
                    meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
                    v_num = p.get("version_num") if p.get("version_num") is not None else meta.get("version_num")
                    if isinstance(v_num, (int, float)) and v_num > max_ver:
                        max_ver = int(v_num)
                    elif isinstance(p.get("version") or meta.get("version"), str):
                        v_str = p.get("version") or meta.get("version")
                        if v_str.startswith("v"):
                            try:
                                v_str_num = int(v_str[1:])
                                if v_str_num > max_ver:
                                    max_ver = v_str_num
                            except ValueError:
                                pass
                if not offset:
                    break
            return (max_ver or 1, f"v{max_ver or 1}")
        except Exception as e:
            print(f"[WARN] Error fetching latest version ({e}). Defaulting to v1.")
            return (1, "v1")

    def _extract_intent_and_filters(self, query: str) -> dict:
        """Parses user query keywords to determine if exact counting or bulk scrolling is required."""
        q_lower = query.lower()
        
        count_keywords = [
            "how many", "count", "number of", "total", "how much",
            "all test cases", "what all", "list all", "list me all",
            "all modules", "list modules", "what modules", "show me all",
            "all categories", "modules in project", "summary of"
        ]
        is_aggregate = any(k in q_lower for k in count_keywords) or ("module" in q_lower and any(w in q_lower for w in ["list", "all", "what", "show"]))

        modules_map = {
            "remove from cart": "Remove from Cart",
            "add to cart": "Add to Cart",
            "browser compatibility": "Browser Compatibility",
            "invoice download": "Invoice",
            "search articles": "Search",
            "select articles": "Select Article",
            "select article": "Select Article",
            "multi select": "Multi Select",
            "login": "Login",
            "browser": "Browser Compatibility",
            "dashboard": "Dashboard",
            "cart": "Cart",
            "payout": "Payout",
            "payment": "Payment",
            "invoice": "Invoice",
            "search": "Search",
            "select": "Select Article"
        }
        matched_module = None
        for k, v in modules_map.items():
            if re.search(r'\b' + re.escape(k) + r'\b', q_lower):
                matched_module = v
                break

        status_match = None
        for s in ["passed", "failed", "blocked", "untested"]:
            if re.search(r'\b' + re.escape(s) + r'\b', q_lower):
                status_match = s.capitalize()
                break

        priority_match = None
        for p in ["critical", "high", "medium", "low"]:
            if re.search(r'\b' + re.escape(p) + r'\b', q_lower):
                priority_match = p.capitalize()
                break

        return {
            "is_aggregate": is_aggregate,
            "module": matched_module,
            "status": status_match,
            "priority": priority_match
        }

    def build(
        self,
        user_query: Union[str, Any],
        project_name: str,
        qdrant_url: str = "http://qdrant:6333",
        qdrant_api_key: Optional[str] = None,
        mistral_api_key: Optional[str] = None,
        top_k: int = 15,
        intent_dict: Optional[Union[Data, Dict[str, Any], Any]] = None,
        qdrant_node_results: Optional[Any] = None,
    ) -> List[Data]:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
        except ImportError:
            raise ImportError("Please install qdrant-client: pip install qdrant-client")

        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None)

        # 0. Detect whether metadata fields are nested under 'metadata.' (Langflow Qdrant component format)
        prefix = self._detect_payload_prefix(client, project_name)

        # 1. Enforce Latest Version Pre-Filter
        latest_ver_num, latest_ver_str = self._get_latest_version_num(client, project_name)
        print(f"[INFO] Hybrid Retriever targeting Project '{project_name}' (Active Version: {latest_ver_str}, Prefix: '{prefix}')")

        # Extract clean string query
        if hasattr(user_query, "text") and getattr(user_query, "text"):
            q_str = getattr(user_query, "text")
        elif isinstance(user_query, dict) and "text" in user_query:
            q_str = str(user_query["text"])
        else:
            q_str = str(user_query)

        # 2. Analyze query for intent & payload filters (Use wired intent_dict if available, else extract)
        intent = None
        if isinstance(intent_dict, Data) and isinstance(intent_dict.data, dict):
            intent = intent_dict.data
        elif isinstance(intent_dict, dict):
            intent = intent_dict
        
        if not isinstance(intent, dict) or not any(k in intent for k in ["is_aggregate", "module", "status", "priority"]):
            intent = self._extract_intent_and_filters(q_str)
        
        must_conditions = []
        if latest_ver_num > 0:
            must_conditions.append(
                models.FieldCondition(key=f"{prefix}version_num", match=models.MatchValue(value=latest_ver_num))
            )

        # 3. MODE A: Exact Scroll Aggregation (Bypasses Top-K cap!)
        if intent.get("is_aggregate"):
            print(f"[INFO] Aggregate/Count Query Detected (`{q_str}`). Routing to Qdrant Exact Scroll...")
            if intent.get("module"):
                must_conditions.append(
                    models.FieldCondition(key=f"{prefix}module", match=models.MatchValue(value=intent["module"]))
                )
            if intent.get("status"):
                must_conditions.append(
                    models.FieldCondition(key=f"{prefix}status", match=models.MatchValue(value=intent["status"]))
                )
            if intent.get("priority"):
                must_conditions.append(
                    models.FieldCondition(key=f"{prefix}priority", match=models.MatchValue(value=intent["priority"]))
                )

            query_filter = models.Filter(must=must_conditions) if must_conditions else None

            all_records = []
            offset = None
            while True:
                records, offset = client.scroll(
                    collection_name=project_name,
                    scroll_filter=query_filter,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset
                )
                all_records.extend(records)
                if not offset:
                    break

            total_matches = len(all_records)
            confidence_score = 1.0 if total_matches > 0 else 0.0

            # Automatically calculate exact breakdown across all retrieved records
            mod_counts = {}
            status_counts = {}
            for r in all_records:
                p = r.payload or {}
                meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
                mod = p.get("module") or meta.get("module", "Unknown Module")
                stat = p.get("status") or meta.get("status", "Unknown Status")
                mod_counts[mod] = mod_counts.get(mod, 0) + 1
                status_counts[stat] = status_counts.get(stat, 0) + 1

            mod_breakdown_str = "\n".join([f"  - **{m}**: {c} test cases" for m, c in sorted(mod_counts.items())])
            status_breakdown_str = "\n".join([f"  - **{s}**: {c} test cases" for s, c in sorted(status_counts.items())])

            summary_header = (
                f"### [EXACT AGGREGATION & INVENTORY FROM QDRANT DATABASE]\n"
                f"- **Project Name**: `{project_name}`\n"
                f"- **Active Data Version**: `{latest_ver_str}`\n"
                f"- **Filtered Module/Category**: `{intent.get('module') or 'All Modules'}`\n"
                f"- **Filtered Status**: `{intent.get('status') or 'Any Status'}`\n"
                f"- **Filtered Priority**: `{intent.get('priority') or 'Any Priority'}`\n"
                f"- **TOTAL MATCHING RECORDS**: **{total_matches} test cases across {len(mod_counts)} distinct modules**\n\n"
                f"#### Complete Module Inventory & Breakdown:\n{mod_breakdown_str}\n\n"
                f"#### Status Distribution:\n{status_breakdown_str}\n\n"
            )

            sample_blocks = []
            for r in all_records[:40]:
                p = r.payload or {}
                meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
                tid = p.get("tid") or meta.get("tid", "N/A")
                scen = p.get("scenario") or meta.get("scenario", "N/A")
                desc = p.get("description") or meta.get("description", p.get("page_content", meta.get("page_content", "")))[:150]
                sample_blocks.append(f"- **{tid}** (`{scen}`): {desc}...")

            full_context = summary_header + "#### Sample Records:\n" + "\n".join(sample_blocks)
            if total_matches > 40:
                full_context += f"\n... (and {total_matches - 40} more identical structure records matching this filter)"

            retrieval_metadata = {
                "source": "qdrant_exact_scroll",
                "retrieval_type": "exact_scroll",
                "confidence": confidence_score,
                "documents": total_matches,
                "project_name": project_name,
                "version": latest_ver_str
            }

            item = Data(data={"page_content": full_context, "text": full_context, **retrieval_metadata})
            setattr(item, "page_content", full_context)
            setattr(item, "metadata", retrieval_metadata)
            return [item]

        # 4. MODE B: Dense Semantic Similarity Search (mistral-embed)
        print(f"[INFO] Semantic Query Detected (`{q_str}`). Routing to mistral-embed Top-K={top_k} Search...")
        try:
            from langchain_mistralai import MistralAIEmbeddings
        except ImportError:
            raise ImportError("Please install langchain-mistralai: pip install langchain-mistralai")

        api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("Must provide 'mistral_api_key' for dense semantic vector search.")

        embedder = MistralAIEmbeddings(model="mistral-embed", mistral_api_key=api_key)
        query_vector = embedder.embed_query(q_str)

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        if hasattr(client, "search"):
            results = client.search(
                collection_name=project_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            )
        else:
            query_res = client.query_points(
                collection_name=project_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            )
            results = query_res.points

        # Calculate exact semantic confidence score from top Qdrant Cosine match scores
        scores = [scored_point.score for scored_point in results if scored_point.score is not None]
        top_score = max(scores) if scores else 0.0
        # Normalize/clamp score between 0.0 and 1.0
        confidence_score = round(max(0.0, min(1.0, float(top_score))), 2)
        print(f"[INFO] Semantic Search Top-1 Cosine Confidence Score: {confidence_score}")

        documents = []
        for scored_point in results:
            payload = scored_point.payload or {}
            content = payload.get("page_content", json.dumps(payload))
            
            # Attach structured confidence metadata wrapper to every retrieved document
            doc_metadata = {
                **payload,
                "retrieval_type": "semantic",
                "confidence": confidence_score,
                "documents": len(results),
                "item_score": round(float(scored_point.score or 0.0), 3),
                "project_name": project_name,
                "version": latest_ver_str
            }
            item = Data(data={"page_content": content, "text": content, **doc_metadata})
            setattr(item, "page_content", content)
            setattr(item, "metadata", doc_metadata)
            documents.append(item)

        if not documents:
            # Return a zero-confidence placeholder data item so guardrail intercepts cleanly
            fallback_meta = {"confidence": 0.0, "documents": 0, "retrieval_type": "semantic", "project_name": project_name}
            item = Data(data={"page_content": "No matching records found.", "text": "No matching records found.", **fallback_meta})
            setattr(item, "page_content", "No matching records found.")
            setattr(item, "metadata", fallback_meta)
            return [item]

        return documents
