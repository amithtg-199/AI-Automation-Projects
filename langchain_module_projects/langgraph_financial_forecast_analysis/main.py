from agents.financial_researcher_agent import finance_audit_agent

def main():
    try:
        initial_state = {"topic": input("Enter your query: ")}
        output = finance_audit_agent.invoke(initial_state)

        print(output["final_output"])
    except KeyboardInterrupt:
        print("\nExiting the session! Have a nice day.\n")

if __name__ == "__main__":
    main()

