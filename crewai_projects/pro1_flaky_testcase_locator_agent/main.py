from agent.agent import crew
def main():
    print("Starting Flaky Test case Validator..")

    inputs = {
        "jira_1": "SU-10",
        "jira_2": "SU-11",
        "file_1": "result1.json",
        "file_2": "result2.json",
    }

    try:
        output = crew.kickoff(inputs=inputs)
        token_usage = output.token_usage
        print("--------------Flaky Test Analysis Report-----------------")
        print(f"Prompt Tokens: {token_usage.prompt_tokens}")
        print(f"Completion Tokens: {token_usage.completion_tokens}")
        print(f"Total Tokens:  {token_usage.total_tokens}")
        print(output)
    except Exception as e:
        print(f"Encountered an exception while executing the agent: '{e}'")

if __name__ == "__main__":
    main()
