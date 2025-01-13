from dataclasses import Field, dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, HttpUrl, PositiveFloat, PositiveInt
from enum import Enum

@dataclass
class Branch(Enum):
    "01" = "Dolnoslaskie"
    "02" = "KujawskoPomorskie"
    "03" = "Lubelskie"
    "04" = "Lubuskie"
    "05" = "Lodzkie"
    "06" = "Malopolskie"
    "07" = "Mazowieckie"
    "08" = "Opolskie"
    "09" = "Podkarpackie"
    "10" = "Podlaskie"
    "11" = "Pomorskie"
    "12" = "Slaskie"
    "13" = "Swietokrzyskie"
    "14" = "WarminskoMazurskie"
    "15" = "Wielkopolskie"
    "16" = "Zachodniopomorskie"

@dataclass
class AgreementAttributes(BaseModel):
    """Represents the attributes of an agreement."""
    code: Optional[str]
    technical_code: Optional[str] = Field(alias="technical-code")
    origin_code: Optional[str] = Field(alias="origin-code")
    service_type: Optional[str] = Field(alias="service-type")
    service_name: Optional[str] = Field(alias="service-name") 
    amount: Optional[PositiveFloat]
    updated_at: Optional[datetime] = Field(alias="updated-at")
    provider_code: Optional[str] = Field(alias="provider-code")
    provider_nip: Optional[str] = Field(alias="provider-nip")
    provider_regon: Optional[str] = Field(alias="provider-regon")
    provider_registry_number: Optional[str] = Field(alias="provider-registry-number")
    provider_name: Optional[str] = Field(alias="provider-name")
    provider_place: Optional[str] = Field(alias="provider-place")
    year: Optional[PositiveInt]
    branch: Optional[Branch]

    class Config:
        """Configuration for field aliases and other settings."""
        populate_by_name = True

class AgreementLinks(BaseModel):
    first_page: Optional[HttpUrl] = Field(None, alias="first")
    prev_page: Optional[HttpUrl] = Field(None, alias="prev")
    self_page: Optional[HttpUrl] = Field(None, alias="self") 
    next_page: Optional[HttpUrl] = Field(None, alias="next") 
    last_page: Optional[HttpUrl] = Field(None, alias="last") 
    related_pages: Optional[HttpUrl] = Field(None, alias="related") 

class Agreement(BaseModel):
    """Represents an agreement."""
    id: str
    type: str = "agreement"
    attributes: AgreementAttributes
    links: AgreementLinks

    class Config:
        """Configuration for the Agreement model."""
        populate_by_name = True

class AgreementsData(BaseModel):
    agreements: List[Agreement]

class AgreementsMeta(BaseModel):
    context: Optional[HttpUrl] = Field(alias="@context")
    count: Optional[PositiveInt]
    page: Optional[PositiveInt]
    limit: Optional[PositiveInt]
    title: Optional[str] = "agreement"
    url: Optional[HttpUrl]
    provider: Optional[str]
    date_published: Optional[datetime] = Field(alias="date-published")
    date_modified: Optional[datetime] = Field(alias="date-modified")
    description: Optional[str]
    keywords: Optional[str]
    language: Optional[str]
    content_type: Optional[str] = Field(alias="content-type")
    is_part_of: Optional[str] = Field(alias="is-part-of")
    version: Optional[str]

class AgreementsPage(BaseModel):
    meta: AgreementsMeta
    links: Optional[AgreementLinks]
    data: AgreementsData




 