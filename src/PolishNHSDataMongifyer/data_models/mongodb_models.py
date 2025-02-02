from typing import List, Optional, Tuple
from pydantic import BaseModel, PositiveFloat


class AgreementInfo(BaseModel):
    id: str
    code: str
    origin_code: str
    service_type: str
    service_name: str
    amount: PositiveFloat
    provider_code: str
    year: int

class ProviderInfo(BaseModel):
    code: str
    nip: str
    regon: str
    registry_number: str
    name: str
    phone: Optional[str]
    agreements: Optional[List[str]]

class Location(BaseModel):
    type: str = "Point"
    coordinates: Tuple[ float, float ] 

class ProviderGeoData(BaseModel):
    code: str
    city: str
    street: str
    building_number: str
    district: Optional[str]
    post_code: str
    voivodeship: str
    location: Location