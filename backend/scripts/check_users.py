import os
import asyncio
from dotenv import load_dotenv

# Load env variables for Supabase
load_dotenv(os.path.join("d:/learning path hackathon/backend", ".env"))

from backend.services.supabase_adapter import get_supabase_adapter

async def main():
    adapter = get_supabase_adapter()
    # Let's see if we can query auth.users using service role key
    res = adapter.client.table("learners").select("user_id").limit(2).execute()
    print("Learners:", res.data)

if __name__ == "__main__":
    asyncio.run(main())
