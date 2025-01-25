from typing import List
from pydantic import BaseModel

class CrawlSchema(BaseModel):
    domains: List[str]

class ProductURLSchema(BaseModel):
    url: str