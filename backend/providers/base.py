from abc import ABC, abstractmethod
from typing import List, Optional
from backend.core.schemas import Occupation, Skill

class ProviderError(Exception):
    pass

class ProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def check_health(self) -> str:
        """Returns 'CONNECTED', 'NOT_CONFIGURED', 'AUTH_REQUIRED', etc."""
        pass

    @abstractmethod
    async def search_occupations(self, query: str, limit: int = 10) -> List[Occupation]:
        pass

    @abstractmethod
    async def get_occupation_details(self, occupation_id: str) -> Optional[Occupation]:
        pass
