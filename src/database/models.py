from datetime import datetime
from pydantic import BaseModel, Field

class PortfolioDocument(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    encrypted_holdings: str = Field(..., description="Base64 AES-256-GCM encrypted JSON string of holdings")
    salt: str = Field(..., description="Hex-encoded salt used to derive the encryption key for this user")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class WatchlistDocument(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    encrypted_symbols: str = Field(..., description="Base64 AES-256-GCM encrypted JSON string of symbols")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
