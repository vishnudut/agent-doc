
from context_client import Context7Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Context7Client(
    api_key=os.getenv("CONTEXT7_API_KEY"),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

print("Testing MemMachine resolution...")
print("=" * 50)

# Test with LLM
print("\n1. WITH LLM (use_llm=True):")
library_id = client.resolve_library("MemMachine", use_llm=True)
print(f"   Result: {library_id}")
print(f"   Expected: /MemMachine/MemMachine")
print(f"   Correct: {'✅ YES' if 'MemMachine/MemMachine' in library_id else '❌ NO'}")

# Test without LLM (fallback)
print("\n2. WITHOUT LLM (use_llm=False):")
library_id = client.resolve_library("MemMachine", use_llm=False)
print(f"   Result: {library_id}")
print(f"   (This might be wrong - that's why we need LLM!)")
