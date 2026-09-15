import asyncio
from backend.services.store import FirestoreStore
from backend.services.adk_agents import RootAgentRunner

async def main():
    store = FirestoreStore()
    runner = RootAgentRunner(store)
    
    person_id = "test_user_123"
    message = "Hi, my name is John and I want to be an AI Engineer. I am a College Student."
    
    print("Testing agent runner with message:", message)
    response = await runner.run(person_id, message)
    print("Response JSON:")
    import json
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
