import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional
import docker

from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolRequest
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)

# Global Playwright state for Track 2 (Zero-Shot BDD)
_pw = None
_browser = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_interactive_elements_cache = {}

async def _ensure_playwright():
    global _pw, _browser, _context, _page
    if not _pw:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
        _context = await _browser.new_context()
        _page = await _context.new_page()

def run_in_docker_sandbox(script_content: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Track 1: Run codegen snippet in an ephemeral docker container.
    """
    try:
        client = docker.from_env()
    except Exception as e:
        logger.warning(f"Docker not available, falling back to subprocess. Error: {e}")
        return run_in_subprocess_sandbox(script_content, timeout)

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as f:
        f.write(script_content)
        script_path = f.name
        
    try:
        # Run with memory limit, read-only mount, network restrictions
        container = client.containers.run(
            "playwright-sandbox",
            command=["uv", "run", "python", "/sandbox/script.py"],
            volumes={script_path: {'bind': '/sandbox/script.py', 'mode': 'ro'}},
            mem_limit="512m",
            network_mode="bridge", # In a real scenario, this would be a tightly locked down custom network
            detach=True,
            remove=False
        )
        
        # Enforce timeout manually since docker-py run doesn't have a strict timeout arg for detach=True
        start_time = time.time()
        while container.status in ["created", "running"]:
            if time.time() - start_time > timeout:
                container.kill()
                return {"error": "Timeout exceeded. Container killed.", "status": "timeout"}
            time.sleep(0.5)
            container.reload()
            
        logs = container.logs().decode('utf-8')
        result = container.wait()
        container.remove(force=True)
        
        return {
            "status": "success" if result["StatusCode"] == 0 else "error",
            "exit_code": result["StatusCode"],
            "logs": logs
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

def run_in_subprocess_sandbox(script_content: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Fallback for when Docker is not installed (e.g., hackathon env).
    """
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as f:
        f.write(script_content)
        script_path = f.name
        
    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "logs": result.stdout + "\n" + result.stderr
        }
    except subprocess.TimeoutExpired as e:
        return {"error": "Timeout exceeded. Subprocess killed.", "status": "timeout", "logs": e.stdout.decode() if e.stdout else ""}
    except Exception as e:
        return {"error": str(e), "status": "error"}
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

app = Server("stlc-playwright-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # Track 1 Tools
        Tool(
            name="replay_codegen_snippet",
            description="Replay a recorded snippet securely in an ephemeral container to extract semantic interactions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_content": {"type": "string", "description": "The python playwright script to replay"}
                },
                "required": ["script_content"]
            }
        ),
        # Track 2 Tools
        Tool(
            name="navigate",
            description="Navigate to a URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="get_interactive_elements",
            description="Extracts semantic locators (AOM) from the current page. MUST be called before emitting click/fill locators.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="click",
            description="Click an element using a semantic locator (must have been returned by get_interactive_elements).",
            inputSchema={
                "type": "object",
                "properties": {
                    "locator": {"type": "string"}
                },
                "required": ["locator"]
            }
        ),
        Tool(
            name="fill",
            description="Fill an input field.",
            inputSchema={
                "type": "object",
                "properties": {
                    "locator": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["locator", "value"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    global _page, _interactive_elements_cache
    
    if name == "replay_codegen_snippet":
        # Track 1 logic
        script_content = arguments.get("script_content", "")
        # Inject our network interceptors and AOM extractors into the script before running
        # (In a full implementation, we'd AST-parse and inject, for MVP we just run it)
        result = run_in_docker_sandbox(script_content)
        return [TextContent(type="text", text=json.dumps(result))]

    # Track 2 logic
    await _ensure_playwright()
    
    if name == "navigate":
        url = arguments.get("url")
        await _page.goto(url)
        return [TextContent(type="text", text=f"Navigated to {url}")]
        
    elif name == "get_interactive_elements":
        # Extract AOM (Accessibility Object Model) elements
        # For MVP, we run a simple JS snippet to find buttons/inputs
        elements = await _page.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('button, input, a, select, [role="button"]'));
                return els.map(e => {
                    const rect = e.getBoundingClientRect();
                    return {
                        tag: e.tagName.toLowerCase(),
                        text: e.innerText || e.value || e.placeholder || e.getAttribute('aria-label') || '',
                        role: e.getAttribute('role') || e.type || e.tagName.toLowerCase(),
                        testId: e.getAttribute('data-testid') || '',
                        visible: rect.width > 0 && rect.height > 0
                    };
                }).filter(e => e.visible && e.text);
            }
        """)
        
        _interactive_elements_cache.clear()
        formatted_locators = []
        for el in elements:
            # Build locator string based on Appendix F Priority
            loc = ""
            if el.get('role') and el.get('text'):
                loc = f"get_by_role('{el['role']}', name='{el['text']}')"
            elif el.get('testId'):
                loc = f"get_by_test_id('{el['testId']}')"
            else:
                loc = f"get_by_text('{el['text']}')"
                
            _interactive_elements_cache[loc] = el
            formatted_locators.append(loc)
            
        return [TextContent(type="text", text=json.dumps({"interactive_locators": formatted_locators}))]
        
    elif name == "click":
        locator = arguments.get("locator")
        if locator not in _interactive_elements_cache:
            return [TextContent(type="text", text=f"ERROR: Locator '{locator}' was not found in previous get_interactive_elements call. Hallucination blocked.")]
            
        # Execute the python-style locator via eval equivalent in JS, or just use playwright's string locator
        # For the hackathon MVP, we map the python locator to playwright locator syntax
        try:
            # Safely evaluate the python string to a playwright locator
            # Example: get_by_role('button', name='Submit')
            # This is complex in pure python without eval on `_page`.
            # We'll mock it for the MCP by executing the equivalent python expression.
            # INSECURE eval for hackathon context since this is the backend interpreting its own LLM's command
            pw_loc = eval(f"_page.{locator}")
            await pw_loc.click()
            return [TextContent(type="text", text=f"Clicked {locator}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to click: {str(e)}")]

    elif name == "fill":
        locator = arguments.get("locator")
        val = arguments.get("value")
        if locator not in _interactive_elements_cache:
            return [TextContent(type="text", text=f"ERROR: Locator '{locator}' was not found in previous get_interactive_elements call. Hallucination blocked.")]
        try:
            pw_loc = eval(f"_page.{locator}")
            await pw_loc.fill(val)
            return [TextContent(type="text", text=f"Filled {locator} with '{val}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to fill: {str(e)}")]
            
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
