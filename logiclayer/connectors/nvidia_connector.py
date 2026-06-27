# connectors/nvidia_connector.py
import httpx
import os
from dotenv import load_dotenv
from logiclayer.connectors.base import AgentConnector

load_dotenv()

class NvidiaConnector(AgentConnector):
    
    def __init__(self, model: str = "meta/llama-3.1-8b-instruct"):
        self.model = model
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def send(self, prompt: str) -> str:
        try:
            if not self.api_key:
                raise ValueError(
                "NVIDIA_API_KEY not set. "
                "Add it to your .env file."
                )
            
            response = httpx.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out — NVIDIA API took too long")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError("Invalid API key — check your .env file")
            elif e.response.status_code == 429:
                raise RuntimeError("Rate limit hit — too many requests")
            else:
                raise RuntimeError(f"API error {e.response.status_code}")
        
        except httpx.NetworkError:
            raise RuntimeError("Network error — check your internet connection")