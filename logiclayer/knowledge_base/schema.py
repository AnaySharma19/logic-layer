from pydantic import BaseModel, Field


class Source(BaseModel):
    source_id: str = Field(..., description="Unique string identifier for the source (e.g., src_001)")
    name: str = Field(..., description="The title of the source document or website")
    url: str = Field(..., description="The direct URL link to the verified source")
    domain: str = Field(..., description="The bare domain this source lives on (e.g., python.org) -- used by trusted_sources whitelist matching")
    category: str = Field(..., description="Topic category this source belongs to (e.g., science_general, health_medicine)")
    retrieved_at: str = Field(..., description="Date this source was checked/scraped, ISO format YYYY-MM-DD")


class Fact(BaseModel):
    fact_id: str = Field(..., description="Unique string identifier for the fact (e.g., fact_001)")
    statement: str = Field(..., description="The full factual statement, used for both exact-match and embedding search")
    source_id: str = Field(..., description="The associated source ID tracking back to the source model")
