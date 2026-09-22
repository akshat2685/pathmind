import os
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join("d:/learning path hackathon/backend", ".env"))

from backend.services.supabase_adapter import get_supabase_adapter
from backend.services.store import FirestoreStore
from backend.services.college_memory_service import CollegeMemoryService

async def main():
    store = FirestoreStore()
    mem_svc = CollegeMemoryService(store)
    adapter = get_supabase_adapter()
    
    # Create user
    user = adapter.client.auth.admin.create_user({"email": "test12345@example.com", "password": "password123"})
    uid = user.user.id
    
    try:
        mem = await mem_svc.record_short_term_context(uid, "hello", "session_123")
        print("Recorded:", mem)
        
        mems = await mem_svc.get_short_term_memories(uid)
        print("Retrieved:", mems)
        
        lmem = await mem_svc.record_long_term_memory(uid, "test long", "test long")
        print("Recorded Long:", lmem)
        
        lmems = await mem_svc.get_long_term_memories(uid)
        print("Retrieved Long:", lmems)
        
    finally:
        adapter.client.auth.admin.delete_user(uid)

if __name__ == "__main__":
    asyncio.run(main())
