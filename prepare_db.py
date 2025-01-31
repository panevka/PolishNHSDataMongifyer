from datetime import date, datetime
import time
import json
import logging
import os
import traceback
from typing import Any, List, Type
from pydantic import BaseModel, TypeAdapter, ValidationError
from pathlib import Path
import requests
import sys
from dotenv import load_dotenv

sys.path.append('../PolishNHSDataMongifyer')
from data_models import Agreement, AgreementInfo, AgreementsPage, Branch, DBSetupConfig, Provider, ProviderGeoData, ProviderGeoEntry, ProviderInfo, ProvidersPage, Response, Result, ServiceType

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")   
    ]
)
logger = logging.getLogger(__name__)

NFZAPI_BASE_URL = "https://api.nfz.gov.pl/app-umw-api"
GEOAPIFY_BASE_URL = "https://api.geoapify.com/v1"

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def fetch(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        full_url = f"{url}?{self._encode_params(params)}" if params else url
        logger.info("Making request to: %s", full_url)
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch data from %s: %s", full_url, e)
            raise
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

        
    def _encode_params(self, params):
        if params:
            from urllib.parse import urlencode
            return urlencode(params)
        return ""
    
class FileDataManagement:
    def __init__(self, branch, service: ServiceType):
        self.FILE_PATH = os.path.abspath(__file__)
        self.FILE_DIR = os.path.dirname(self.FILE_PATH)
        self.OUTPUT_DIR_PATH = os.path.join(self.FILE_DIR, "HealthCareData")
        self.SERVICE_PATH = os.path.join(self.OUTPUT_DIR_PATH, f"SERVICE[{service}]")
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
            logging.error(f"Unexpected error occurred during file structure setup: {str(e)}")
            logging.error(traceback.format_exc())

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
            logging.error(f"Unexpected error occurred while creating {filename} file: {str(e)}")
            logging.error(traceback.format_exc())

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
            logging.error(f"ValueError occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())
    
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
            logging.error(f"ValueError occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())
                

class HealthcareDataProcessing:

    def __init__(self, branch: Branch, service: ServiceType):
        self.branch = branch
        self.service = service
        self._FileManager = FileDataManagement(branch, service)
        self._FileManager.setup_file_structure()

    def has_next_page(agreements_page: AgreementsPage|ProvidersPage):
       return agreements_page.links is not None and agreements_page.links.next_page is not None

    def process_agreements(self, year=2025, limit=25, startPage=1):
        params = {
            "year": year,
            "branch": self.branch,
            "serviceType":self.service,
            "page": startPage,
            "limit": limit,
            "format": "json",
            "api-version": 1.2
        }
        next_page = True

        while (next_page):
            try:
                response_data = APIClient(NFZAPI_BASE_URL).fetch(endpoint='agreements', params=params)  
                parsed_response = Validation.validate(response_data, AgreementsPage)
                next_page = HealthcareDataProcessing.has_next_page(parsed_response)
                agreements = parsed_response.data.agreements
                page_number = parsed_response.meta.page
                
                serialized_agreements = [agreement.model_dump(by_alias=True) for agreement in agreements]
                self._FileManager.save_agreements_page(page_data=serialized_agreements, page_number=page_number,
                                            request_page_limit=limit)
                params["page"] += 1  
            except Exception as e:
                logging.error(f"Unexpected error occurred while processing agreements: {str(e)}")
                logging.error(traceback.format_exc())

    def get_provider_info(self, provider_code: str) -> Provider:
        params = {
            "code": provider_code,
            "branch": str(self.branch),
            "limit": 1,
            "format": "json",
            "api-version": 1.2
        }
        
        try:
            response_data = APIClient(NFZAPI_BASE_URL).fetch(endpoint='providers', params=params)  
            parsed_response = ProvidersPage(**response_data)
            providers = parsed_response.data.entries
            return providers[0]
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

    def process_output_providers(self):
        agreements_path = self._FileManager.AGREEMENTS_DATA_DIR
        processed_providers = []
        try:
            for page_file in os.listdir(agreements_path):
                page_path = os.path.join(agreements_path, page_file)
                with open(page_path, 'r') as json_file:
                    data = json.load(json_file)
                    agreements = Validation.validate_list(data, Agreement)
                    for agreement in agreements:
                        if agreement.attributes.provider_code not in processed_providers:
                            provider_data = self.get_provider_info(agreement.attributes.provider_code)
                            if(provider_data):
                                self._FileManager.save_provider(provider_data)
                                processed_providers.append(provider_data.attributes.code)
        except Exception as e:
            logging.error(f"Unexpected error occurred while processing providers: {str(e)}")
            logging.error(traceback.format_exc())

    def get_provider_geographical_data(provider: Provider) -> Result:
        attr = provider.attributes
        apiKey = os.getenv("GEOAPIFY_KEY")
        params = {
            "city": attr.place,
            "street": attr.street,
            "postcode": attr.post_code,
            "country": "Poland",
            "lang": "pl",
            "limit": 1,
            "type": "amenity",
            "format": "json",
            "filter": "countrycode:pl",
            "bias" : "countrycode:pl",
            "apiKey": apiKey
        }
        try:
            data = APIClient(GEOAPIFY_BASE_URL).fetch(endpoint="geocode/search", params=params)
            res = Validation.validate(data, Response)
            return res.results[0]
        except Exception as e:
            logging.error(f"Unexpected error occurred while fetching provider geographical data: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    def process_provider_geographical_data(self):
        input_file = self._FileManager.PROVIDERS_DATA
        with open(input_file, "r") as file:
            try:
                data = json.load(file)
                # print(typ)
                providers = Validation.validate_list(data, Provider)
                for provider in providers:
                    try:
                        geo_data = HealthcareDataProcessing.get_provider_geographical_data(provider)
                        geo_result = Validation.validate(geo_data, Result)
                        self._FileManager.save_provider_geo_data(provider, geo_result)
                    except Exception as e:
                        logging.error(f"Error while processing geographical data of providers: {str(e)}")
                        logging.error(traceback.format_exc())

            except ValidationError as e:
                logging.error(f"Cannot validate providers in {input_file}: {str(e)}")
                logging.error(traceback.format_exc())
            except Exception as e:
                logging.error(f"Unexpected error occurred while processing geographical data of providers: {str(e)}")
                logging.error(traceback.format_exc())

class DatabaseSetup:                          
    def __init__(self, configs: List[DBSetupConfig]):
        for config in configs:
            self.branch = config.branch.value
            self.NHS_processor = HealthcareDataProcessing(self.branch, config.service_type.value)
            self.NHS_file_manager = self.NHS_processor._FileManager
            self.NHS_processor.process_agreements()
            self.NHS_processor.process_output_providers()
            self.NHS_processor.process_provider_geographical_data()
            
            self.establish_provider_info_collection()
            self.establish_provider_geo_collection()
            self.establish_agreements_collection()
        
    def get_provider_by_code(self, provider_code: str, providers_list: List[Provider]) -> Provider:
        for provider in providers_list:
            if(provider.attributes.code == provider_code):
                return provider
        return None

    def establish_provider_info_collection(self):

        providers_path = self.NHS_file_manager.PROVIDERS_DATA
        agreements_path = self.NHS_file_manager.AGREEMENTS_DATA_DIR

        try:
            provider_file = open(providers_path, "r")
            providers_data = json.load(provider_file)
            providers_list = Validation.validate_list(providers_data, Provider)
        except ValidationError as e:
            logging.error(f"Could not validate data of providers for branch {self.branch}: {str(e)}")
            logging.error(traceback.format_exc())


        collection_path = self.NHS_file_manager.PROVIDERS_COLLECTION
        processed_codes_of_entries = []

        for page in os.listdir(agreements_path):
            try:
                page_path = os.path.join(agreements_path, page)
                with open(page_path, "r") as agreements_file:
                    agreements_list = json.load(agreements_file)
                    agreements = Validation.validate_list(agreements_list, Agreement)
                    for agreement in agreements:
                        try:
                            provider = self.get_provider_by_code(agreement.attributes.provider_code, providers_list)
                            if(provider):
                                with open(collection_path, "r") as f:
                                    try:
                                        collection_data = json.load(f)
                                        validated_collection_entries = Validation.validate_list(collection_data, ProviderInfo)
                                    except ValidationError:
                                        collection_entries_list = []
                                    except json.JSONDecodeError:
                                        collection_entries_list = []

                                if any(entry_code == agreement.attributes.provider_code for entry_code in processed_codes_of_entries):
                                    for entry in validated_collection_entries:
                                        if entry.code == agreement.attributes.provider_code:
                                            entry.agreements.append(agreement.id)
                                            break
                                    collection_entries_list = [e.model_dump() for e in validated_collection_entries]
                                else:
                                    try:
                                        p = ProviderInfo(
                                        code = provider.attributes.code,
                                        nip = provider.attributes.nip,
                                        registry_number = provider.attributes.registry_number,
                                        name = provider.attributes.name,
                                        phone = provider.attributes.phone,
                                        regon = provider.attributes.regon,
                                        agreements=[agreement.id])
                                        collection_entries_list.append(p.model_dump())
                                        processed_codes_of_entries.append(p.code)
                                    except ValidationError as e:
                                        logging.error(f"Error while ProviderInfo collection member in branch: {self.branch}: {str(e)}")
                                        logging.error(traceback.format_exc())

                                with open(collection_path, "w") as f:
                                    json.dump(collection_entries_list, f, indent=4)
                                    provider_file.seek(0)
                        except Exception as e:
                            logging.error(f"Error while creating agreements collection for branch: {self.branch}: {str(e)}")
                            logging.error(traceback.format_exc())

            except Exception as e:
                logging.error(f"Could not establish ProviderInfo collection for branch {self.branch}: {str(e)}")
                logging.error(traceback.format_exc())

    def establish_provider_geo_collection(self):

        geodata_path = self.NHS_file_manager.PROVIDERS_GEO_DATA
        collection_file_path = self.NHS_file_manager.PROVIDERS_GEO_COLLECTION

        with open(collection_file_path, "r") as collection_file_read:
            try:
                geo_collection_data = json.load(collection_file_read)
                Validation.validate_list(geo_collection_data, ProviderGeoEntry)
            except json.JSONDecodeError:
                geo_collection = []

        with open(geodata_path, "r") as geodata_file:
            try:
                geodata = json.load(geodata_file)
                geodata_list = Validation.validate_list(geodata, ProviderGeoEntry)

                with open(collection_file_path, "w") as collection_file_write:
                    for entry in geodata_list:
                        try:
                            provider_collection_entry = ProviderGeoData(
                                code = entry.code,
                                city = entry.geo_data.city,
                                street = entry.geo_data.street,
                                building_number=entry.geo_data.housenumber,
                                district=entry.geo_data.district,
                                post_code = entry.geo_data.postcode,
                                voivodeship=entry.branch,
                                location = { "type": "Point", "coordinates": [entry.geo_data.lon, entry.geo_data.lat]}
                            )
                            geo_collection.append(provider_collection_entry.model_dump())
                            json.dump(geo_collection, collection_file_write, indent=4)
                            collection_file_write.seek(0)
                        except ValidationError as e:
                            logging.error(f"Couldn't create ProviderGeoCollection member for branch {self.branch}: {str(e)}")
                            logging.error(traceback.format_exc())
                        except json.JSONDecodeError:
                            logging.error(f"Couldn't create ProviderGeoCollection member for branch {self.branch}: {str(e)}")
            except ValidationError as e:
                logging.error(f"Could not validate data in {geodata_path}")
                logging.error(traceback.format_exc())
            except Exception as e:
                logging.error(f"Unexpected error occurred: {str(e)}")
                logging.error(traceback.format_exc())

    def establish_agreements_collection(self):

        data_path = self.NHS_file_manager.AGREEMENTS_DATA_DIR
        collection_file_path = self.NHS_file_manager.AGREEMENTS_COLLECTION

        for page in os.listdir(data_path):
            page_path = os.path.join(data_path, page)
            with open(page_path, "r") as page_file:
                page_data= json.load(page_file)
                agreements_list = Validation.validate_list(page_data, Agreement)
                with open(collection_file_path, "r") as collection_file_read:
                    try:
                        agreements_collection = json.load(collection_file_read)
                        Validation.validate_list(agreements_collection, AgreementInfo)
                    except json.JSONDecodeError:
                        agreements_collection = []
                    except ValidationError:
                        agreements_collection = []

                for agreement in agreements_list:
                    try:
                        agreement_info_entry = AgreementInfo(
                            id = agreement.id,
                            code = agreement.attributes.code,
                            origin_code = agreement.attributes.origin_code,
                            service_type = agreement.attributes.service_type,
                            service_name = agreement.attributes.service_name,
                            amount = agreement.attributes.amount,
                            provider_code= agreement.attributes.provider_code,
                            year = agreement.attributes.year
                        )

                        with open(collection_file_path, "w") as collection_file_write:
                            agreements_collection.append(agreement_info_entry.model_dump())
                            json.dump(agreements_collection, collection_file_write, indent=4)
                            collection_file_write.seek(0)
                    except ValidationError as e:
                        logging.error(f"Could not create AgreementsCollection member: {str(e)}")
                        logging.error(traceback.format_exc())
                    except Exception as e:
                        logging.error(f"Could not write to agreements collection file: {str(e)}")
                        logging.error(traceback.format_exc())


class Validation:
    @staticmethod
    def validate(variable: Any, model: Type[BaseModel]) -> BaseModel:
        try:
            return model(**variable) if isinstance(variable, dict) else model.model_validate(variable)
        except ValidationError as e:
            logging.error(f"Validation failed: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    @staticmethod
    def validate_list(items: List[Any], model: Type[BaseModel]) -> List[BaseModel]:
        try:
            return TypeAdapter(List[model]).validate_python(items)
        except ValidationError as e:
            logging.error(f"Validation failed: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    @staticmethod
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))
    
        
def main():
    list = [{ "branch": "12", "year": 2025, "service_type": "04"}, {"branch": "12", "year": 2025, "service_type": "11"}, 
            {"branch": "10", "year": 2025, "service_type": "04"}, {"branch": "10", "year": 2025, "service_type": "11"}]
    validated_list = Validation.validate_list(list, DBSetupConfig)
    db = DatabaseSetup(validated_list)

main()