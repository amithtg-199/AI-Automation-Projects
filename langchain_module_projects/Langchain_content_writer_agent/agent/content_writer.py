from utils.llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Safety Fallback for LLM models in case of Errors.
def get_safe_llm_fallback(primary_llm: str, fallback_llm: list):

    valid_fallbacks = [llm for llm in fallback_llm if fallback_llm is not None]

    if not primary_llm:
        if valid_fallbacks:
            return valid_fallbacks[0].with_fallbacks(valid_fallbacks[1:])
        raise ValueError("No valid LLM instances available.")

    return primary_llm.with_fallbacks(valid_fallbacks)

# Init LLM
llm = get_safe_llm_fallback(primary_llm=get_llm("mistral"), fallback_llm=[get_llm("openai"),get_llm("anthropic")])

# Accept Chat prompt from user in realtime
prompt = ChatPromptTemplate.from_messages([
    ("system", "Your a Vetran Reseacher with 10 years of experience in scraping data from Web based on user query, and provide in depth analysis, always respond with context relavent to user query only. Always return output in a proper text format with proper spacing and formatting just like your writing a reasearch paper."),
    ("human", "{user_input}")
])

# Setup chain of events
chain = prompt | llm | StrOutputParser()


