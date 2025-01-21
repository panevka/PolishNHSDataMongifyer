from datetime import date, datetime
import time
import json
import logging
import os
import traceback
from typing import Any, Dict, List, Type
from pydantic import BaseModel, TypeAdapter, ValidationError, parse_obj_as
from pathlib import Path
import requests
import sys
from dotenv import load_dotenv

sys.path.append('../PolishNHSDataMongifyer')
from data_models import Agreement, AgreementInfo, AgreementsData, AgreementsPage, Branch, Provider, ProviderGeoData, ProviderGeoEntry, ProviderInfo, ProvidersPage, Response, Result

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

error_handler = logging.FileHandler("errors.log")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger.addHandler(error_handler)  # Attach error handler

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
    def __init__(self, branch):
        self.FILE_PATH = os.path.abspath(__file__)
        self.FILE_DIR = os.path.dirname(self.FILE_PATH)
        self.OUTPUT_DIR_PATH = os.path.join(self.FILE_DIR, "HealthCareData")
        self.BRANCH_PATH = os.path.join(self.OUTPUT_DIR_PATH, self.get_voivodeship_name(branch))

        self.DATA_DIR = os.path.join(self.BRANCH_PATH, "Data" )
        self.AGREEMENTS_DATA_DIR = os.path.join(self.DATA_DIR, "Agreements")
        self.PROVIDERS_DATA = os.path.join(self.DATA_DIR, "ProvidersData.json")
        self.PROVIDERS_GEO_DATA = os.path.join(self.DATA_DIR, "ProvidersGeographicalData.json")

        self.COLLECTION_DIR = os.path.join(self.BRANCH_PATH, "Collections" )
        self.PROVIDERS_COLLECTION = os.path.join(self.COLLECTION_DIR, "ProvidersInfoCollection.json")
        self.PROVIDERS_GEO_COLLECTION = os.path.join(self.COLLECTION_DIR, "ProvidersGeoCollection.json")
        self.AGREEMENTS_COLLECTION = os.path.join(self.COLLECTION_DIR, "AgreementsCollection.json")

    def SetupFileStructure(self):
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

    def __init__(self, branch: Branch):
        self.branch = branch
        self._FileManager = FileDataManagement(branch)
        self._FileManager.SetupFileStructure()

    def has_next_page(agreements_page: AgreementsPage|ProvidersPage):
       return agreements_page.links is not None and agreements_page.links.next_page is not None

    def process_agreements(self, year=2025, service_type="04", limit=25, startPage=1):
        params = {
            "year": year,
            "branch": self.branch,
            "serviceType": service_type,
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
    def establish_provider_info_collection(branch: Branch):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HealthCareData", FileDataManagement.get_voivodeship_name(branch))
        provider_path = os.path.join(data_path, "Providers.json")
        provider_file = open(provider_path, "r")
        for page in os.listdir(data_path):
            if page == "Providers.json" or page == "ProvidersGeographicalData.json" or page == "ProvidersCollection.json":
                continue
            
            file_path = os.path.join(data_path, page)
            with open(file_path, "r") as agreements_file:
                AgreementsList = TypeAdapter(List[Agreement])
                agreements_list = json.load(agreements_file)
                agreements = AgreementsList.validate_python(agreements_list)
                for agreement in agreements:
                    ProvidersList = TypeAdapter(List[Provider])
                    providers_data = json.load(provider_file)
                    providers = ProvidersList.validate_python(providers_data)
                    for provider in providers:
                        if(provider.attributes.code == agreement.attributes.provider_code):
                            p = ProviderInfo(
                            code = provider.attributes.code,
                            nip = provider.attributes.nip,
                            registry_number = provider.attributes.registry_number,
                            name = provider.attributes.name,
                            phone = provider.attributes.phone,
                            regon = provider.attributes.regon,
                            agreements=[agreement.id])
                            path = os.path.join(data_path, "ProvidersCollection.json")
                            p = p.model_dump()

                            with open(path, "r") as f:
                                try:
                                    providers_list = json.load(f) 
                                    if not isinstance(providers_list, list):
                                        providers_list = []
                                except json.JSONDecodeError:
                                    providers_list = []

                                ProviderInfoList = TypeAdapter(List[ProviderInfo])
                                if(len(providers_list) > 0):
                                    provs = ProviderInfoList.validate_python(providers_list)
                                    if any(pr.code == agreement.attributes.provider_code for pr in provs):
                                        for pr in provs:
                                            if pr.code == agreement.attributes.provider_code:
                                                pr.agreements.append(agreement.id)
                                                break
                                        providers_list = [prov.model_dump() for prov in provs]
                                    else:
                                        providers_list.append(p)
                                else:
                                    providers_list.append(p)

                            with open(path, "w") as f:
                                json.dump(providers_list, f, indent=4)
                            provider_file.seek(0)

    def establish_provider_geo_collection(branch: Branch):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HealthCareData", FileDataManagement.get_voivodeship_name(branch))
        geodata_path = os.path.join(data_path, "ProvidersGeographicalData.json")
        collection_file_path = os.path.join(data_path, "ProviderGeoCollection.json")
        
        with open(geodata_path, "r") as geodata_file:
            geodata = json.load(geodata_file)

            with open(collection_file_path, "r") as collection_file_read:
                try:
                    geo_collection = json.load(collection_file_read)
                    if not isinstance(geo_collection, list):
                        geo_collection = []
                except json.JSONDecodeError:
                    geo_collection = []

            with open(collection_file_path, "w") as collection_file_write:
                for entry in geodata:
                    processed_entry = ProviderGeoEntry(**entry)
                    provider_collection_entry = ProviderGeoData(
                        code = processed_entry.code,
                        city = processed_entry.geo_data.city,
                        street = processed_entry.geo_data.street,
                        building_number=processed_entry.geo_data.housenumber,
                        district=processed_entry.geo_data.district,
                        post_code = processed_entry.geo_data.postcode,
                        voivodeship=processed_entry.geo_data.state,
                        location = { "type": "Point", "coordinates": [processed_entry.geo_data.lon, processed_entry.geo_data.lon]}
                    )
                    geo_collection.append(provider_collection_entry.model_dump())
                    json.dump(geo_collection, collection_file_write, indent=4)
                    collection_file_write.seek(0)

    def establish_agreements_collection(branch: Branch):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HealthCareData", FileDataManagement.get_voivodeship_name(branch))
        collection_file_path = os.path.join(data_path, "AgreementsCollection.json")
        
        for page in os.listdir(data_path):

            if page.startswith("Page") is False: 
                continue

            page_path = os.path.join(data_path, page)
            with open(page_path, "r") as page_file:
                page_data= json.load(page_file)
                with open(collection_file_path, "r") as collection_file_read:
                    try:
                        agreements_collection = json.load(collection_file_read)
                        if not isinstance(agreements_collection, list):
                            agreements_collection = []
                    except json.JSONDecodeError:
                        agreements_collection = []

                for agreement in page_data:
                    agr = Agreement(**agreement)
                    agreement_info_entry = AgreementInfo(
                        id = agr.id,
                        code = agr.attributes.code,
                        origin_code = agr.attributes.origin_code,
                        service_type = agr.attributes.service_type,
                        service_name = agr.attributes.service_name,
                        amount = agr.attributes.amount,
                        provider_code= agr.attributes.provider_code,
                        year = agr.attributes.year
                    )

                    with open(collection_file_path, "w") as collection_file_write:
                        agreements_collection.append(agreement_info_entry.model_dump())
                        json.dump(agreements_collection, collection_file_write, indent=4)
                        collection_file_write.seek(0)

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
    HealthcareDataProcessing("10").process_provider_geographical_data()

main()