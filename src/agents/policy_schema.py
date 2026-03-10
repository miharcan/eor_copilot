from typing import List, Optional
from pydantic import BaseModel, Field


class PolicySection(BaseModel):
    section_id: Optional[str] = None
    title: str
    text: str


class PolicyDocument(BaseModel):
    doc_id: str
    country: str
    policy_type: str
    version: Optional[int] = None
    last_updated: str = Field(..., description="YYYY-MM-DD")
    sections: List[PolicySection]
