from pydantic import BaseModel, Field
from .geoapify_models import Result
from .nhs_api_models import Branch, ServiceType


class DBSetupConfig(BaseModel):
    branch: Branch
    year: int = 2025
    service_type: ServiceType

class ProviderGeoEntry(BaseModel):
    code: str = Field(alias="provider-code")
    branch: str = Field(alias="provider-branch")
    geo_data: Result = Field(alias="geo-data")