import re
import json
from typing import Dict, Any, Union

from langflow.custom import Component
from langflow.io import Output, HandleInput
from langflow.schema import Data

class QueryIntentRouter(Component):
    display_name = "Query Intent Router"
    description = "Classifies user query intent (Count/Bulk vs Semantic Search) and extracts target metadata filters (`module`, `status`, `priority`) for the Adaptive Hybrid Retriever."
    icon = "split"

    inputs = [
        HandleInput(
            name="user_query",
            display_name="User Query / Question (Connect Chat Input)",
            input_types=["Message", "str", "Any"],
            required=True
        ),
    ]

    outputs = [
        Output(display_name="Intent Dict", name="intent_payload", method="build_intent")
    ]

    def build_intent(self) -> Data:
        res = self.build(
            user_query=getattr(self, "user_query", "")
        )
        return Data(data=res)

    def build_config(self):
        return {
            "user_query": {"display_name": "User Query / Question (Connect Chat Input)", "field_type": "HandleInput", "input_types": ["Message", "str", "Any"], "required": True},
        }

    def build(self, user_query: Union[str, Any]) -> Dict[str, Any]:
        if hasattr(user_query, "text") and getattr(user_query, "text"):
            q_str = getattr(user_query, "text")
        elif isinstance(user_query, dict) and "text" in user_query:
            q_str = str(user_query["text"])
        else:
            q_str = str(user_query)
        q_lower = q_str.lower()
        
        # Check for count / bulk aggregation keywords
        count_keywords = [
            "how many", "count", "number of", "total", "how much",
            "all test cases", "what all", "list all", "list me all",
            "all modules", "list modules", "what modules", "show me all",
            "all categories", "modules in project", "summary of"
        ]
        is_aggregate = any(k in q_lower for k in count_keywords) or ("module" in q_lower and any(w in q_lower for w in ["list", "all", "what", "show"]))

        # Extract target modules if mentioned
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

        # Extract status if mentioned
        status_match = None
        for s in ["passed", "failed", "blocked", "untested"]:
            if re.search(r'\b' + re.escape(s) + r'\b', q_lower):
                status_match = s.capitalize()
                break

        # Extract priority if mentioned
        priority_match = None
        for p in ["critical", "high", "medium", "low"]:
            if re.search(r'\b' + re.escape(p) + r'\b', q_lower):
                priority_match = p.capitalize()
                break

        router_payload = {
            "user_query": q_str,
            "is_aggregate": is_aggregate,
            "module": matched_module,
            "status": status_match,
            "priority": priority_match,
            "routing_mode": "Exact Scroll Aggregation (Mode A)" if is_aggregate else "Dense Semantic Vector Search (Mode B)"
        }
        print(f"[INFO] Query Intent Router Output: {json.dumps(router_payload, indent=2)}")
        return router_payload

if __name__ == "__main__":
    router = QueryIntentRouter()
    print("Test 1:", router.build("how many test cases are there for login scenario"))
    print("Test 2:", router.build("how to verify credit card 3D secure timeouts"))
