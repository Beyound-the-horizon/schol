
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

load_dotenv()

if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY is missing from .env")

search = TavilySearch(
    max_results=3,
    topic="general",
)

try:
    result = search.invoke({
        "query": "official Erasmus Mundus Joint Masters scholarship 2027"
    })
    print(result)
except Exception as e:
    print(f"Search failed: {type(e).__name__}: {e}")
