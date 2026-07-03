from datetime import datetime
from typing import Optional, List, Dict
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

class UserProfileDocument(BaseModel):
    user_id: str = Field(..., description="Unique username or ID")
    email: str = Field(..., description="User's email address")
    password_hash: str = Field(..., description="Hashed master password for logins")
    salt: str = Field(..., description="Salt used for hashing the password")
    is_verified: bool = Field(default=False, description="Email verification status")
    phone: Optional[str] = Field(default=None, description="Optional phone number")
    encrypted_broker_credentials: Optional[str] = Field(default=None, description="Encrypted broker API details")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class PreferencesDocument(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    currency: str = Field(default="INR", description="Default display currency")
    language: str = Field(default="en", description="Default interface language")
    market: str = Field(default="IN", description="Target region/market")
    theme: str = Field(default="dark", description="Visual theme preference")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class AlertDocument(BaseModel):
    user_id: str = Field(..., description="User ID associated with the alert")
    alert_id: str = Field(..., description="Unique ID for the alert")
    symbol: str = Field(..., description="Stock ticker symbol (e.g. RECLTD.NS)")
    alert_type: str = Field(..., description="Type: PRICE, VOLUME, DIVIDEND, NEWS, RESULTS, CORP_ACTION")
    condition: str = Field(..., description="ABOVE, BELOW, TRIGGER")
    target_value: str = Field(..., description="Threshold price, volume trigger, or event string")
    status: str = Field(default="ACTIVE", description="ACTIVE, PAUSED, TRIGGERED")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_at: Optional[datetime] = Field(default=None)

    class Config:
        populate_by_name = True
