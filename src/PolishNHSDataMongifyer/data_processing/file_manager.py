import json
import os
from pathlib import Path
import traceback

from pydantic import ValidationError
from src.PolishNHSDataMongifyer.data_models.custom_models import ProviderGeoEntry
from src.PolishNHSDataMongifyer.data_models.geoapify_models import Result
from src.PolishNHSDataMongifyer.data_models.nhs_api_models import Branch, Provider, ServiceType
from src.PolishNHSDataMongifyer.validation.validation import Validation

from src.PolishNHSDataMongifyer.logging.logger import get_logger
logger = get_logger(__name__)

class FileDataManagement:
    def __init__(self, branch, service: ServiceType, path: Path):
        self.FILE_DIR = os.path.dirname(path)
        self.OUTPUT_DIR_PATH = os.path.join(self.FILE_DIR, "HealthCareData")
        self.SERVICE_PATH = os.path.join(self.OUTPUT_DIR_PATH, f"SERVICE[{service.name}]")
        self.BRANCH_PATH = os.path.join(self.SERVICE_PATH, self.get_voivodeship_name(branch))

        self.DATA_DIR = os.path.join(self.BRANCH_PATH, "Data" )
        self.AGREEMENTS_DATA_DIR = os.path.join(self.DATA_DIR, "Agreements")
        self.PROVIDERS_DATA = os.path.join(self.DATA_DIR, "ProvidersData.json")
        self.PROVIDERS_GEO_DATA = os.path.join(self.DATA_DIR, "ProvidersGeographicalData.json")

        self.COLLECTION_DIR = os.path.join(self.BRANCH_PATH, "Collections" )
        self.PROVIDERS_COLLECTION = os.path.join(self.COLLECTION_DIR, "ProvidersInfoCollection.json")
        self.PROVIDERS_GEO_COLLECTION = os.path.join(self.COLLECTION_DIR, "ProvidersGeoCollection.json")
        self.AGREEMENTS_COLLECTION = os.path.join(self.COLLECTION_DIR, "AgreementsCollection.json")

    def setup_file_structure(self):
        try:
            Path(self.OUTPUT_DIR_PATH).mkdir(parents=True, exist_ok=True)
            Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
            Path(self.COLLECTION_DIR).mkdir(parents=True, exist_ok=True)
            
            Path(self.PROVIDERS_COLLECTION).touch()
            Path(self.PROVIDERS_GEO_COLLECTION).touch()
            Path(self.AGREEMENTS_COLLECTION).touch()

            Path(self.PROVIDERS_DATA).touch()
            Path(self.PROVIDERS_GEO_DATA).touch()

            Path(self.AGREEMENTS_DATA_DIR).mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            logger.error(f"Unexpected error occurred during file structure setup: {str(e)}")
            logger.error(traceback.format_exc())

    @staticmethod
    def get_voivodeship_name(branch_code: str):
        for name, code in Branch.__members__.items():
            if code.value == branch_code:
                return name
        raise ValueError(f"Could not find proper voivodeship name for branch code: '{branch_code}'")

    def save_agreements_page(self, page_data, page_number: int, request_page_limit: int):
        try:
            filename = f"Page{page_number}_limit{request_page_limit}.json"
            file_path = os.path.join(self.AGREEMENTS_DATA_DIR, filename)
            
            with open(file_path, "w") as file:
                json.dump(page_data, file, indent=4, default=Validation.json_serial)
        except Exception as e:
            logger.error(f"Unexpected error occurred while creating {filename} file: {str(e)}")
            logger.error(traceback.format_exc())

    def save_provider(self, provider: Provider):
        try:
            with open(self.PROVIDERS_DATA, "r") as file:
                try:
                    providers_list = json.load(file)
                    Validation.validate_list(providers_list, Provider)
                except json.JSONDecodeError:
                    providers_list = []
                except ValidationError:
                    providers_list = []

            providers_list.append(provider.model_dump(by_alias=True))
            with open(self.PROVIDERS_DATA, "w") as file:
                json.dump(providers_list, file, ensure_ascii=False, indent=4)

        except ValueError as e:
            logger.error(f"ValueError occurred: {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            logger.error(traceback.format_exc())
    
    def save_provider_geo_data(self, provider: Provider, geo_data: Result):
        try:
            file_path = self.PROVIDERS_GEO_DATA
            with open(file_path, "r") as file:
                try:
                    providers_list = json.load(file)
                    Validation.validate_list(providers_list, ProviderGeoEntry)
                except json.JSONDecodeError:
                    providers_list = []
                except ValidationError:
                    providers_list = []

            provider_entry = {
                "provider-code": provider.attributes.code,
                "provider-branch": provider.attributes.branch,
                "geo-data": geo_data.model_dump(by_alias=True)
            }
            providers_list.append(provider_entry)
            with open(file_path, "w") as file:
                json.dump(providers_list, file, ensure_ascii=False, indent=4, default=Validation.json_serial)

        except ValueError as e:
            logger.error(f"ValueError occurred: {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            logger.error(traceback.format_exc())
                