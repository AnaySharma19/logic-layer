# logiclayer/connectors/base.py
from abc import ABC, abstractmethod

class AgentConnector(ABC):
    
    @abstractmethod
    def __init__(self, model: str):
        """
        Args:
            model: The model name to use
        """
        pass

    @abstractmethod
    def send(self, prompt: str) -> str:
        """
        Args:
            prompt: The user prompt string
            
        Returns:
            raw_response: The raw text response from the agent
        """
        pass