from typing import List, Optional
from pydantic import BaseModel, HttpUrl


class Bbox(BaseModel):
    lon1: float
    lat1: float
    lon2: float
    lat2: float

class DataSource(BaseModel):
    sourcename: Optional[str]
    attribution: str
    license: str
    url: Optional[HttpUrl] = None

class Timezone(BaseModel):
    name: Optional[str] = None
    offset_STD: str
    offset_STD_seconds: int
    offset_DST: str
    offset_DST_seconds: int
    abbreviation_STD: str
    abbreviation_DST: str

class Rank(BaseModel):
    importance: Optional[float] = None
    popularity: Optional[float] = None
    confidence: float
    confidence_city_level: float
    confidence_street_level: float
    confidence_building_level: float
    match_type: str

class QueryParsed(BaseModel):
    housenumber: Optional[str] = None
    street: Optional[str] = None
    postcode: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    expected_type: Optional[str] = None

class Query(BaseModel):
    text: Optional[str] = None 
    housenumber: Optional[str] = None 
    street: Optional[str] = None
    postcode: Optional[str] = None 
    city: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    parsed: Optional[QueryParsed] = None

class Result(BaseModel):
    datasource: DataSource
    name: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    county: Optional[str] = None
    city: str
    hamlet: Optional[str] = None
    municipality: Optional[str] = None
    postcode: str
    street: str
    lon: float
    lat: float
    housenumber: str
    result_type: Optional[str] = None
    formatted: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    timezone: Optional[Timezone] = None
    plus_code: Optional[str] = None
    plus_code_short: Optional[str] = None
    rank: Optional[Rank] = None
    place_id: Optional[str] = None

class Response(BaseModel):
    results: List[Result]
    query: Query