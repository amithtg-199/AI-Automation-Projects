import json
from typing import List, Dict, Any, Union

from langflow.custom import Component
from langflow.io import HandleInput, StrInput, FloatInput, Output
from langflow.schema import Data, Message

class ContextBuilder(Component):
    display_name = "Context Builder & Guardrail Interceptor"
    description = "Wraps retrieved Qdrant records in structured JSON metadata (`confidence`, `documents`, `retrieval_type`) and intercepts queries where confidence < 0.5 with explicit guardrail fallback."
    icon = "shield-alert"

    inputs = [
        HandleInput(
            name="retrieved_data",
            display_name="Retrieved Data / Documents",
            input_types=["Data", "Table", "Message", "DataFrame", "str", "Any"],
            required=True,
            is_list=True
        ),
        StrInput(name="project_name", display_name="Project Name", value="ecommerce_test_cases"),
        FloatInput(name="confidence_threshold", display_name="Confidence Guardrail Threshold", value=0.50),
    ]

    outputs = [
        Output(display_name="Context Message (For Prompt Template)", name="context_message", method="build_context_message"),
        Output(display_name="Context Data", name="context_data", method="build_context_data"),
        Output(display_name="Context Text", name="context_text", method="build_context_text")
    ]

    def build_context_message(self) -> Message:
        res = self.build(
            retrieved_data=getattr(self, "retrieved_data", []),
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            confidence_threshold=getattr(self, "confidence_threshold", 0.50),
        )
        return Message(text=res)

    def build_context_data(self) -> Data:
        res = self.build(
            retrieved_data=getattr(self, "retrieved_data", []),
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            confidence_threshold=getattr(self, "confidence_threshold", 0.50),
        )
        return Data(data={"text": res, "context": res})

    def build_context_text(self) -> str:
        return self.build(
            retrieved_data=getattr(self, "retrieved_data", []),
            project_name=getattr(self, "project_name", "ecommerce_test_cases"),
            confidence_threshold=getattr(self, "confidence_threshold", 0.50),
        )

    def build_config(self):
        return {
            "retrieved_data": {"display_name": "Retrieved Data / Documents", "field_type": "HandleInput", "input_types": ["Data", "Table", "Message", "DataFrame", "str", "Any"], "required": True},
            "project_name": {"display_name": "Project Name", "field_type": "str", "value": "ecommerce_test_cases"},
            "confidence_threshold": {"display_name": "Confidence Guardrail Threshold", "field_type": "float", "value": 0.50},
        }

    def build(
        self,
        retrieved_data: Union[List[Data], List[Dict[str, Any]], str],
        project_name: str = "ecommerce_test_cases",
        confidence_threshold: float = 0.50
    ) -> str:
        # Default safety wrapper values
        confidence = 0.0
        documents_count = 0
        retrieval_type = "semantic"
        formatted_context = ""

        if not retrieved_data:
            confidence = 0.0
            documents_count = 0
        elif isinstance(retrieved_data, str):
            formatted_context = retrieved_data
            confidence = 1.0 if "EXACT AGGREGATION" in retrieved_data else 0.5
            documents_count = 1
        elif isinstance(retrieved_data, list) and len(retrieved_data) > 0:
            first_item = retrieved_data[0]
            meta = first_item.metadata if hasattr(first_item, "metadata") else first_item.get("metadata", {})
            
            # Extract confidence and metadata from first retrieved document
            confidence = float(meta.get("confidence", 0.0))
            documents_count = int(meta.get("documents", len(retrieved_data)))
            retrieval_type = str(meta.get("retrieval_type", "semantic"))

            # Check if it's Mode A exact scroll report
            if meta.get("source") == "qdrant_exact_scroll" or retrieval_type == "exact_scroll":
                formatted_context = first_item.page_content if hasattr(first_item, "page_content") else str(first_item)
            else:
                # Format Mode B semantic matches into clean markdown
                context_lines = [f"### [SEMANTIC TOP-K MATCHES FROM QDRANT DATABASE (`{project_name}`)]\n"]
                for idx, item in enumerate(retrieved_data, 1):
                    content = item.page_content if hasattr(item, "page_content") else str(item.get("page_content", item))
                    item_meta = item.metadata if hasattr(item, "metadata") else item.get("metadata", {})
                    
                    tid = item_meta.get("tid", f"Match #{idx}")
                    scen = item_meta.get("scenario", item_meta.get("module", "N/A"))
                    prio = item_meta.get("priority", "N/A")
                    stat = item_meta.get("status", "N/A")
                    auto = item_meta.get("is_automated", "N/A")
                    score = item_meta.get("item_score", "N/A")

                    context_lines.append(
                        f"#### {idx}. Test Case `{tid}` | Scenario: **{scen}** (Similarity: `{score}`)\n"
                        f"- **Priority**: `{prio}` | **Status**: `{stat}` | **Automated**: `{auto}`\n"
                        f"```text\n{content.strip()}\n```\n"
                    )
                formatted_context = "\n".join(context_lines)

        # CHECK GUARDRAIL THRESHOLD (< 0.50)
        if confidence < confidence_threshold or documents_count == 0:
            print(f"[GUARDRAIL ALERT] Retrieval Confidence ({confidence}) is below threshold ({confidence_threshold}). Intercepting output.")
            guardrail_wrapper = {
                "context": (
                    "[GUARDRAIL TRIGGERED: LOW RETRIEVAL CONFIDENCE]\n"
                    f"The vector similarity confidence score ({confidence}) is lower than the required safety threshold ({confidence_threshold}).\n"
                    "MANDATORY SYSTEM INSTRUCTION: You MUST NOT attempt to answer the user query or fabricate test cases. "
                    "You MUST respond ONLY with the exact safety string:\n"
                    "\"I could not find relevant information in the knowledge base to answer your question.\""
                ),
                "confidence": confidence,
                "documents": documents_count,
                "retrieval_type": retrieval_type,
                "guardrail_status": "TRIGGERED_LOW_CONFIDENCE"
            }
            return json.dumps(guardrail_wrapper, indent=2)

        # Output structured JSON wrapper with valid context
        success_wrapper = {
            "context": formatted_context,
            "confidence": confidence,
            "documents": documents_count,
            "retrieval_type": retrieval_type,
            "guardrail_status": "PASSED"
        }
        return json.dumps(success_wrapper, indent=2)

if __name__ == "__main__":
    builder = ContextBuilder()
    # Test high confidence pass
    high_doc = Document(page_content="Verify positive login...", metadata={"confidence": 0.94, "documents": 8, "retrieval_type": "semantic", "tid": "TC_0001"})
    print("--- High Confidence Test (0.94) ---")
    print(builder.build([high_doc]))
    
    # Test low confidence guardrail intercept (< 0.50)
    low_doc = Document(page_content="Irrelevant document...", metadata={"confidence": 0.32, "documents": 1, "retrieval_type": "semantic"})
    print("\n--- Low Confidence Guardrail Intercept Test (0.32) ---")
    print(builder.build([low_doc]))
