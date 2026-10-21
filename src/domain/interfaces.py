from abc import ABC, abstractmethod
from src.types import StoreDataCollection

class FileExtractionStrategy(ABC):
    @abstractmethod
    def extract_raw_files(self) -> StoreDataCollection:
        pass