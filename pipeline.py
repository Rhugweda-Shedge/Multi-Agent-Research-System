import warnings
import re
warnings.filterwarnings("ignore", category=DeprecationWarning)

from agents import build_search_agent, writer_chain, critic_chain, revise_chain
from tools import scrape_url

def run_research_pipeline(topic: str) -> dict:
    
    state = {}

    # step 1: search agent
    print("\n" + "="*50)
    print("Step 1: search agent working...")
    print("="*50)

    search_agent = build_search_agent()
    search_result =search_agent.invoke({
        "messages": [("user", f"Find recent reliable and detailed information on the topic: {topic}")]
    })

    state["search_results"] = search_result['messages'][-1].content

    print("\n Search result: ", state["search_results"])

    # step 2: scrape top 2 URLs from search results
    print("\n" + "="*50)
    print("Step 2: scraping top 2 URLs from search results...")
    print("="*50)

    urls = re.findall(r"URL: (https?://\S+)", state["search_results"])
    scraped_parts = []
    for url in urls[:2]:
        content = scrape_url.invoke(url)
        scraped_parts.append(f"[{url}]\n{content}")

    state["scraped_content"] = "\n\n---\n\n".join(scraped_parts) if scraped_parts else "No content scraped."

    print("\n Scraped content: ", state["scraped_content"])

    # Step 3 - Writer chain
    print("\n" + "="*50)
    print("Step 3: writer is drafting the report...")
    print("="*50)

    research_combined = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\n Final report:\n", state["report"])

    # Critic Report
    print("\n" + "="*50)
    print("Step 4: critic is reviewing the report...")
    print("="*50)

    state["feedback"] = critic_chain.invoke({
        "topic": topic,
        "report": state["report"],
    })

    print("\n Critic report:\n", state["feedback"])

    # Step 5 — Conditional revision if score < 7
    score_match = re.search(r"Score:\s*(\d+)", state["feedback"])
    score = int(score_match.group(1)) if score_match else 10

    if score < 7:
        print("\n" + "="*50)
        print(f"Step 5: score {score}/10 — writer revising based on critic feedback...")
        print("="*50)

        state["report"] = revise_chain.invoke({
            "topic": topic,
            "report": state["report"],
            "feedback": state["feedback"],
        })
        state["revised"] = True
        print("\n Revised report:\n", state["report"])
    else:
        state["revised"] = False

    return state

if __name__ == "__main__":
    topic = input("\nEnter the research topic: ")
    run_research_pipeline(topic)