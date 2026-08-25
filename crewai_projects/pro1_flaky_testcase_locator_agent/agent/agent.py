import os
import requests
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

ENV_PATH = Path(__file__).resolve().parent.parent/"config"/".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Tool to fetch Jira Attachmet and load data.
@tool("Fetch result.json attachment from JIRA_ID and send to the Agent")
def fetch_jira_attachment(issue_id: str, target_file: str) -> str:
    """
    Downloads and returns the raw text content of a specified attachment file from a single Jira issue.
    """
    jira_url = os.getenv("JIRA_SERVER")
    auth = HTTPBasicAuth(username=os.getenv("JIRA_EMAIL"), password=os.getenv("JIRA_API_TOKEN"))
    headers = {"Accept": "application/json"}

    res = requests.get(url=f"{jira_url}/rest/api/3/issue/{issue_id}",
                       auth=auth,
                       headers=headers)
    if res.status_code != 200:
        return f"Error fetching issue {issue_id}: {res.status_code}"
    jira_response_json = res.json()
    attachments = jira_response_json.get("fields", {}).get("attachment", [])

    attachment_url = None
    for attachment in attachments:
        if attachment["filename"] == target_file:
            attachment_url = attachment["content"]
            break

    if attachment_url:
        jira_attachment_data = requests.get(url=attachment_url, auth=auth, headers=headers)

        # Added Exception handling
        if jira_attachment_data.status_code != 200:
            return f"Error fetching attachment from {attachment_url} returned response code:'{jira_attachment_data.status_code}'"

        try:
            jira_json_data = jira_attachment_data.json()
            if not isinstance(jira_json_data, dict):
                return "Attachment data is not a valid 'Key:value' pair"
        except json.JSONDecodeError as e:
            return f"Unable to parse data, Attachment does not contain valid JSON data, returned error '{e}'"
    else:
        # Try fetching data from description.
        jira_description = jira_response_json.get("fields", {}).get("description")

        # If no data in Jira exception handling.
        if not jira_description:
            return f"Description is empty for Jira_id: '{issue_id}'"

        try:
            if isinstance(jira_description, str):
                jira_json_data = json.loads(jira_description)
            elif isinstance(jira_description, dict):
                jira_json_data = jira_description
            else:
                return "Unable to parse data, Description data is unrecognized"
        except (json.JSONDecodeError, TypeError) as e:
            return f"Unable to parse data, Description does not contain valid JSON data, returned error '{e}'"
        

    def _parse_json_data():
        test_data = {}
        for suite in jira_json_data.get("suites", []):
            for spec in suite.get("specs", []):
                spec_key = f"[{spec.get('id')}] {spec.get('title')}"
                test_data[spec_key] = {
                    "file": spec.get("file"),
                    "line": spec.get("line"),
                    "tags": spec.get("tags", []),
                    "ok": spec.get("ok"),
                    "tests": spec.get("tests", [])
                }
        return json.dumps(test_data, indent=2)
    return _parse_json_data()

#Initialize LLM
def get_llm(provider: Optional[str] = None) -> LLM:
    """Returns the requested LLM instance"""
    provider = (provider or os.getenv("ACTIVE_LLM_PROVIDER", "mistral")).lower()

    if provider == "mistral":
        return LLM(
            model="codestral-latest",
            base_url="https://codestral.mistral.ai/v1",
            api_key=os.getenv("MISTRAL_API_KEY")
        )
    elif provider == "groq":
        return LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY")
        )
    elif provider == "openai":
        return LLM(
            model="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif provider == "anthropic":
        return LLM(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    elif provider == "ollama":
        return LLM(
            model="ollama/qwen2.5-coder:32b",
            base_url="http://localhost:11434"
        )
    else:
        # Fallback default if an unknown provider name is supplied
        return LLM(
            model="codestral-latest",
            base_url="https://codestral.mistral.ai/v1",
            api_key=os.getenv("MISTRAL_API_KEY")
        )

# Initialize Agent
flaky_test_case = Agent(
    role="Playwright Flakiness Specialist",
    goal="Diagnose, root causes of non-deterministic playwright failures",
    backstory="You are an expert QA Automation engineer expert in Playwright debugging",
    tools=[fetch_jira_attachment],
    llm=get_llm()
)

# Create Task
result_analysis = Task(
    description=(
        "1. Call `fetch_jira_attachment` to fetch data for issue_id {jira_1} with target_file {file_1}. \n"
        "2. Call `fetch_jira_attachment` to fetch data for issue_id {jira_2} with target_file {file_2}. \n"
        "3. Load both results in formatted JSON Structure"
        "4. Compare tests across both runs, Identify specs that passed in one run but failed or timed out in the other or test case with inconsistent results.\n"
        "5. Output a structured Markdown report summarizing flaky tests, error stack traces, and proposed fixes."
    ),
    expected_output="A structured report detailing flaky tests, execution delta between runs, and recommendations.",
    agent=flaky_test_case
)

# Execute Crew
crew = Crew(
    agents=[flaky_test_case],
    tasks=[result_analysis],
    process=Process.sequential,
    verbose=True,
    memory=False,
)