import os
import pytest
import asyncio
from backend.services.store import FirestoreStore

@pytest.mark.asyncio
async def test_firestore_emulator_persistence():
    # Only run this if we have configured the emulator
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("FIRESTORE_EMULATOR_HOST not set, skipping E2E persistence test")

    store = FirestoreStore()
    assert store._available is True, "Store should connect to the emulator"

    health = await store.check_health()
    assert health == "CONNECTED", "Emulator should return CONNECTED"

    # 1. Test isolated writes
    person_id = "test-e2e-user"
    goal_data = {"target_outcome": "Senior E2E Engineer", "version": 1}
    
    await store.save_goal(person_id, goal_data)
    
    # 2. Test reads (persistence)
    retrieved_goal = await store.get_goal(person_id)
    assert retrieved_goal is not None
    assert retrieved_goal["target_outcome"] == "Senior E2E Engineer"
    
    # 3. Test overwrite / versioning
    goal_data_v2 = {"target_outcome": "Principal E2E Engineer", "version": 2}
    await store.save_goal(person_id, goal_data_v2)
    retrieved_goal_v2 = await store.get_goal(person_id)
    assert retrieved_goal_v2["target_outcome"] == "Principal E2E Engineer"
    assert retrieved_goal_v2["version"] == 2
