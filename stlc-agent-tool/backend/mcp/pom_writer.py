import ast
from typing import List, Dict, Any

class POMWriter:
    """
    Utility to generate Page Object Models following Appendix F & I.
    Enforces web-first assertions and CSS/XPath fallback comments.
    """
    
    @staticmethod
    def generate_pom_class(page_name: str, elements: List[Dict[str, Any]]) -> str:
        """
        Generates a Python POM class based on the extracted AOM elements.
        """
        lines = [
            "from playwright.sync_api import Page, expect",
            "",
            f"class {page_name}Page:",
            f"    def __init__(self, page: Page):",
            f"        self.page = page"
        ]
        
        for el in elements:
            name = POMWriter._sanitize_name(el.get("text") or el.get("role") or "element")
            locator = POMWriter._build_locator(el)
            lines.append(f"        self._{name} = self.page.{locator}")
            
        lines.append("")
        
        # Add basic interaction methods
        for el in elements:
            name = POMWriter._sanitize_name(el.get("text") or el.get("role") or "element")
            lines.append(f"    def click_{name}(self):")
            lines.append(f"        self._{name}.click()")
            lines.append("")
            
            if el.get("tag") == "input":
                lines.append(f"    def fill_{name}(self, text: str):")
                lines.append(f"        self._{name}.fill(text)")
                lines.append("")
                
        return "\n".join(lines)
        
    @staticmethod
    def generate_test_skeleton(page_name: str) -> str:
        """
        Generates a test skeleton enforcing Appendix I best practices.
        """
        return f"""import pytest
from playwright.sync_api import Page, expect
from pages.{page_name.lower()}_page import {page_name}Page

@pytest.mark.smoke
class Test{page_name}:
    def test_basic_flow(self, page: Page):
        {page_name.lower()}_page = {page_name}Page(page)
        
        # TODO: Add interaction logic
        
        # ENFORCED: Web-first assertions only. No bare assert or wait_for_timeout.
        expect(page).to_have_title("Expected Title")
"""
        
    @staticmethod
    def _build_locator(el: Dict[str, Any]) -> str:
        # Appendix F Priority: get_by_role > get_by_label > get_by_placeholder > get_by_text > get_by_test_id > CSS/XPath
        if el.get("role") and el.get("text"):
            return f"get_by_role('{el['role']}', name='{el['text']}')"
        elif el.get("testId"):
            return f"get_by_test_id('{el['testId']}')"
        elif el.get("text"):
            return f"get_by_text('{el['text']}')"
        else:
            # Fallback to generic css if nothing else available (should add a comment as per rules)
            tag = el.get("tag", "div")
            return f"locator('{tag}')  # FALLBACK: Raw CSS selector used due to missing semantic attributes"
            
    @staticmethod
    def _sanitize_name(text: str) -> str:
        clean = "".join(c if c.isalnum() else "_" for c in text.lower())
        return clean.strip("_") or "unknown_element"
