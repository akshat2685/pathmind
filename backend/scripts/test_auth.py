import os
import asyncio
from dotenv import load_dotenv

# Load env variables for Supabase
load_dotenv(os.path.join("d:/learning path hackathon/backend", ".env"))

from backend.services.supabase_adapter import get_supabase_adapter

async def main():
    adapter = get_supabase_adapter()
    # Create test user
    try:
        user = adapter.client.auth.admin.create_user({
            "email": "testuser_memory@example.com",
            "password": "password123",
            "email_confirm": True
        })
        print(f"Created user: {user.user.id}")
        
        # Test insert to memory table
        res = adapter.client.table('pathmind_short_term_memories').insert({
            "user_id": user.user.id,
            "content": "Test memory content",
            "topic": "Test topic"
        }).execute()
        print("Inserted memory:", res.data)
        
        # Cleanup
        adapter.client.auth.admin.delete_user(user.user.id)
        print("Deleted user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
