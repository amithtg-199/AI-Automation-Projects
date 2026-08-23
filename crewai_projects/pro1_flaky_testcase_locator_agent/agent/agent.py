import os, requests, json
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
def fetch_jira_attacthment(issue_id: str, target_file: str) -> str:
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
    attachments = res.json()['fields']['attachment']

    attachtment_url = None
    for attachment in attachments:
        if attachment["filename"] == target_file:
            attachtment_url = attachment["content"]
            break
    if not attachtment_url:
        return f"Error: Attachment {target_file} not found on issue {issue_id}."
    att_data = requests.get(url=attachtment_url, auth=auth, headers=headers)

    def _parse_json_data():
        test_data = {}
        json_data = att_data.json()
        for suite in json_data.get("suites", []):
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

#Initilaize LLM
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
    goal="Diagnoise, root causes of non-deterministic playwright failures",
    backstory="You are an expert QA Automation engineer export in playwright debugging",
    tools=[fetch_jira_attacthment],
    llm=get_llm()
)

# Create Task
result_analysis = Task(
    description=(
        "1. Call `fetch_jira_attacthment` to fetch data for issue_id {jira_1} with target_file {file_1}. \n"
        "2. Call `fetch_jira_attacthment` to fetch data for issue_id {jira_2} with target_file {file_2}. \n"
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

# Input data for crew_AI

inputs = {
    "jira_1": "SU-10",
    "jira_2": "SU-11",
    "file_1": "result1.json",
    "file_2": "result2.json",
}

output = crew.kickoff(inputs=inputs)
token_usage = output.token_usage
print("--------------Flaky Test Analysis Report-----------------")
print(f"Prompt Tokens: {token_usage.prompt_tokens}")
print(f"Prompt Tokens: {token_usage.completion_tokens}")
print(f"Total Tokens:  {token_usage.total_tokens}")
print(output)