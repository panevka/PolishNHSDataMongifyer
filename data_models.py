from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, HttpUrl, PositiveFloat, PositiveInt, Field, condecimal
from enum import Enum

class Branch(str, Enum):
    Dolnoslaskie: str = "01"
    KujawskoPomorskie: str = "02"
    Lubelskie: str = "03"
    Lubuskie: str = "04"
    Lodzkie: str = "05"
    Malopolskie: str = "06"
    Mazowieckie: str = "07"
    Opolskie: str = "08"
    Podkarpackie: str = "09"
    Podlaskie: str = "10"
    Pomorskie: str = "11"
    Slaskie: str = "12"
    Swietokrzyskie: str = "13"
    WarminskoMazurskie: str = "14"
    Wielkopolskie: str = "15"
    Zachodniopomorskie: str = "16"

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

class PageLinks(BaseModel):
    first_page: Optional[HttpUrl] = Field(alias="first")
    prev_page: Optional[HttpUrl] = Field(alias="prev")
    self_page: Optional[HttpUrl] = Field(alias="self") 
    next_page: Optional[HttpUrl] = Field(alias="next") 
    last_page: Optional[HttpUrl] = Field(alias="last") 
    related_pages: Optional[HttpUrl] = Field(alias="related") 

class AgreementLinks(BaseModel):
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

class PageMeta(BaseModel):
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
    meta: PageMeta
    links: Optional[PageLinks]
    data: AgreementsData

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

class ProviderAttributes(BaseModel):
    branch: Optional[Branch]
    code: Optional[str]
    name: Optional[str]
    nip: Optional[str]
    regon: Optional[str]
    registry_number: Optional[str] = Field(alias="registry-number")
    post_code: Optional[str] = Field(alias="post-code")
    street: Optional[str]
    place: Optional[str]
    phone: Optional[str]
    commune: Optional[str]

class Provider(BaseModel):
    type: str = "dictionary-provider-entry"
    attributes: ProviderAttributes

class ProviderData(BaseModel):
    entries: List[Provider]

class ProvidersPage(BaseModel):
    meta: PageMeta
    links: Optional[PageLinks]
    data: ProviderData

class Bbox(BaseModel):
    lon1: float
    lat1: float
    lon2: float
    lat2: float

class DataSource(BaseModel):
    sourcename: str
    attribution: str
    license: str
    url: HttpUrl

class Timezone(BaseModel):
    name: str
    offset_STD: str
    offset_STD_seconds: int
    offset_DST: str
    offset_DST_seconds: int
    abbreviation_STD: str
    abbreviation_DST: str

class Rank(BaseModel):
    importance: float
    popularity: float
    confidence: float
    confidence_city_level: float
    confidence_street_level: float
    confidence_building_level: float
    match_type: str

class QueryParsed(BaseModel):
    housenumber: Optional[str]
    street: Optional[str]
    postcode: Optional[str]
    city: Optional[str]
    country: Optional[str]
    state: Optional[str]
    expected_type: Optional[str]

class Query(BaseModel):
    text: Optional[str]
    housenumber: Optional[str]
    street: Optional[str]
    postcode: Optional[str]
    city: Optional[str]
    country: Optional[str]
    state: Optional[str]
    parsed: QueryParsed

class Result(BaseModel):
    datasource: DataSource
    name: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    state: Optional[str]
    district: Optional[str]
    county: Optional[str]
    city: Optional[str]
    hamlet: Optional[str]
    municipality: Optional[str]
    postcode: Optional[str]
    street: Optional[str]
    lon: float
    lat: float
    housenumber: Optional[str]
    result_type: Optional[str]
    formatted: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    timezone: Timezone
    plus_code: Optional[str]
    plus_code_short: Optional[str]
    rank: Rank
    place_id: str

class Response(BaseModel):
    results: List[Result]
    query: Query

    


 