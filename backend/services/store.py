from google.cloud import firestore
from typing import Optional, Dict, Any
import json
from backend.core.config import settings

class FirestoreStore:
    def __init__(self):
        # Initializes using default GOOGLE_APPLICATION_CREDENTIALS if available
        try:
            self.db = firestore.AsyncClient(project=settings.FIRESTORE_PROJECT_ID)
            self._available = True
        except Exception:
            self.db = None
            self._available = False

    async def check_health(self) -> str:
        if not self._available:
            return "NOT_CONFIGURED"
        try:
            # Simple check to ensure we can list collections
            collections = self.db.collections()
            async for _ in collections:
                break
            return "CONNECTED"
        except Exception:
            return "SOURCE_UNAVAILABLE"

    async def get_cached_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
            
        try:
            doc_ref = self.db.collection('knowledge_cache').document(key)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            # If firestore is misconfigured or API is disabled, just treat as cache miss
            return None
        return None

    async def set_cached_knowledge(self, key: str, data: Dict[str, Any]) -> None:
        if not self._available:
            return
            
        try:
            doc_ref = self.db.collection('knowledge_cache').document(key)
            await doc_ref.set(data)
        except Exception:
            pass

    async def save_assessment_result(self, person_id: str, result_data: Dict[str, Any]) -> None:
        if not self._available:
            return
        try:
            # Use a compound key to prevent overwrites or just auto-id, but we'll use auto-id inside a person's subcollection
            doc_ref = self.db.collection('persons').document(person_id).collection('assessments').document()
            await doc_ref.set(result_data)
        except Exception:
            pass

    async def get_assessment_results(self, person_id: str) -> list[Dict[str, Any]]:
        if not self._available:
            return []
        try:
            docs = self.db.collection('persons').document(person_id).collection('assessments').stream()
            results = []
            async for doc in docs:
                results.append(doc.to_dict())
            return results
        except Exception:
            return []
