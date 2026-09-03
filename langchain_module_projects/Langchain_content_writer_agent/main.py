from agent.content_writer import chain

def main():
    # Input from user
    try:
        topic = input("On what can I research About: ")
    # Call LLM
        response = chain.invoke({"user_input": topic})
        print("Here is the data you requested: \n", response)
    except KeyboardInterrupt:
        print("\nExiting the session! Have a nice day.\n")

if __name__ == "__main__":
    main()