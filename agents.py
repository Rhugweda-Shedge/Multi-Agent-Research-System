from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def _get_llm():
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

def _get_critic_llm():
    return ChatAnthropic(
        model=os.getenv("CRITIC_MODEL", "claude-sonnet-5"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

def build_search_agent():
    return create_agent(model=_get_llm(), tools=[web_search])

def build_scrape_agent():
    return create_agent(model=_get_llm(), tools=[scrape_url])

# Writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

    Topic: {topic}

    Research Gathered:
    {research}

    Structure the report as:
    - Introduction
    - Key Findings (minimum 3 well-explained points)
    - Conclusion
    - Sources (list all URLs found in the research)

    Be detailed, factual and professional."""),
])

# LCEL Pipeline
writer_chain = writer_prompt | _get_llm() | StrOutputParser()

# Critic chain
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

    Original Topic: {topic}

    Report:
    {report}

    Score the report across these 5 dimensions (2 points each, total 10):
    1. Relevance — does it directly answer the topic?
    2. Depth — are findings well-explained with detail?
    3. Sourcing — are credible URLs cited and used?
    4. Accuracy — are claims factual and grounded in the research?
    5. Clarity — is it well-structured and readable?

    Respond in this exact format:

    Score: X/10
    - Relevance: X/2
    - Depth: X/2
    - Sourcing: X/2
    - Accuracy: X/2
    - Clarity: X/2

    Strengths:
    - ...
    - ...

    Areas to Improve:
    - ...
    - ...

    One line verdict:
    ..."""),
])

critic_chain = critic_prompt | _get_critic_llm() | StrOutputParser()

# Revise chain — used when critic score < 7
revise_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Revise reports based on specific feedback."),
    ("human", """Revise the research report below to address the critic's feedback.

    Topic: {topic}

    Original Report:
    {report}

    Critic's Feedback:
    {feedback}

    Keep the same structure (Introduction, Key Findings, Conclusion, Sources).
    Address every specific criticism. Do not just rephrase — improve substance."""),
])

revise_chain = revise_prompt | _get_llm() | StrOutputParser()