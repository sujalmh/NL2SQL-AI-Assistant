from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI  # or another LLM provider
from langchain_core.output_parsers import StrOutputParser

# Define your LLM
llm = ChatOpenAI(temperature=0.4, model="gpt-4o-mini")  # replace with your model or use Ollama

# Prompt template for generating NL explanation
explaination_template = """
You are a data analyst assistant. Based on the user's natural language query and the SQL query result in JSON,
write a brief and clear explanation of what the result means in human language.

User Query:
{query}

SQL Result:
{result_json}

Your Explanation:
"""

explaination_prompt = PromptTemplate.from_template(explaination_template)

# Chain
explanation_chain: Runnable = explaination_prompt | llm

thinking_template = """
You are summarizing internal AI reasoning steps during a data analysis task.
Given a step with its context, generate a one-line summary of what step was just done.

Step: {step}

Respond with a single, clear, past-tense sentence summarizing the step.
"""

thinking_prompt = PromptTemplate.from_template(thinking_template)

# Chain
thinking_chain: Runnable = thinking_prompt | llm

# Function to generate explanation
def generate_nl_explanation(query: str, result: dict) -> str:
    result_json = str(result)
    response = explanation_chain.invoke({"query": query, "result_json": result_json})
    return response.content

def thinking_explanation(step: str) -> str:
    response = thinking_chain.invoke({"step": step})
    return response.content