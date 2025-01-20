import time
import json
import logging
import os
import traceback
from typing import Dict, List
from pydantic import TypeAdapter, parse_obj_as
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
    @staticmethod
    def get_voivodeship_name(branch_code: str):
        for name, code in Branch.__members__.items():
            if code.value == branch_code:
                return name
        raise ValueError(f"Could not find proper voivodeship name for branch code: '{branch_code}'")

    @staticmethod
    def save_page(page_data, branch_code, page_number, request_page_limit):
        try:
            voivodeship = FileDataManagement.get_voivodeship_name(branch_code)
            filename = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "HealthCareData", voivodeship,
                f"Page{page_number}_limit{request_page_limit}.json"
            )
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w") as file:
                file.write(page_data)

        except ValueError as e:
            logging.error(f"ValueError occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

    @staticmethod
    def save_provider(provider_data: Provider, file_path):
        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    try:
                        providers_list = json.load(file) 
                        if not isinstance(providers_list, list):
                            providers_list = []
                    except json.JSONDecodeError:
                        providers_list = []
            else:
                providers_list = []

            providers_list.append(provider_data.model_dump(by_alias=True))
            with open(file_path, "w") as file:
                json.dump(providers_list, file, ensure_ascii=False, indent=4)

        except ValueError as e:
            logging.error(f"ValueError occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())
    
    @staticmethod
    def save_provider_geo_data(provider: Provider, geo_data: Result, file_path):
        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    try:
                        providers_list = json.load(file) 
                        if not isinstance(providers_list, list):
                            providers_list = []
                    except json.JSONDecodeError:
                        providers_list = []
            else:
                providers_list = []


            provider_entry = {
                "provider-code": provider.attributes.code,
                "geo-data": geo_data.model_dump(by_alias=True)
            }
            providers_list.append(provider_entry)
            with open(file_path, "w") as file:
                json.dump(providers_list, file, ensure_ascii=False, indent=4)

        except ValueError as e:
            logging.error(f"ValueError occurred: {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())
                

class HealthcareDataProcessing:

    def has_next_page(agreements_page: AgreementsPage|ProvidersPage):
       return agreements_page.links is not None and agreements_page.links.next_page is not None

    def process_agreements(year=2025, branch="10", service_type="04", limit=25, timeout=1.5, startPage=1):
        params = {
            "year": year,
            "branch": branch,
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
                parsed_response = AgreementsPage(**response_data)
                next_page = HealthcareDataProcessing.has_next_page(parsed_response)
                agreements = parsed_response.data.agreements
                page_number = parsed_response.meta.page
                serialized_agreements = [agreement.model_dump_json(by_alias=True) for agreement in agreements]
                serialized_json = "[" + ",".join(serialized_agreements) + "]"
                pretty_json = json.dumps(json.loads(serialized_json), indent=4)

                FileDataManagement.save_page(pretty_json,
                                            branch_code=branch,
                                            page_number=page_number,
                                            request_page_limit=limit)
                params["page"] += 1  
            except Exception as e:
                logging.error(f"Unexpected error occurred: {str(e)}")
                logging.error(traceback.format_exc())

    def get_provider_info(provider_code: List, branch: Branch, year=2025):
        params = {
            "year": year,
            "code": provider_code,
            "branch": str(branch),
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

    def process_output_providers(branch: Branch):
        branch_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HealthCareData", FileDataManagement.get_voivodeship_name(branch))
        output_file = os.path.join(branch_path, "Providers.json")
        processed_providers = []
        try:
            AgreementsList = TypeAdapter(List[Agreement])
            for page_file in os.listdir(branch_path):
                file_path = os.path.join(branch_path, page_file)
                with open(file_path, 'r') as json_file:
                    data = json.load(json_file)
                    agreements = AgreementsList.validate_python(data)
                    for agreement in agreements:
                        time.sleep(1.3)
                        if agreement.attributes.provider_code not in processed_providers:
                            provider_data = HealthcareDataProcessing.get_provider_info(agreement.attributes.provider_code, branch)
                            if(provider_data):
                                FileDataManagement.save_provider(provider_data, output_file)
                                processed_providers.append(provider_data.attributes.code)
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

    def get_provider_geographical_data(provider: Provider):
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
            res = Response(**data)
            return res.results[0]
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

    def process_provider_geographical_data(branch: Branch):
        branch_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HealthCareData", FileDataManagement.get_voivodeship_name(branch))
        input_file = os.path.join(branch_path, "Providers.json")
        output_file = os.path.join(branch_path, "ProvidersGeographicalData.json")
        with open(input_file, "r") as file:
            try:
                data = json.load(file)
                ProvidersList = TypeAdapter(List[Provider])
                providers = ProvidersList.validate_python(data)
                for provider in providers:
                    geo_data = HealthcareDataProcessing.get_provider_geographical_data(provider)
                    FileDataManagement.save_provider_geo_data(provider, geo_data, output_file)
            except Exception as e:
                logging.error(f"Unexpected error occurred: {str(e)}")
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
                    
def main():
    HealthcareDataProcessing.process_agreements(2025, "16", service_type="04", limit=25, timeout=1.2, startPage=1)
    HealthcareDataProcessing.process_output_providers("16")
    DatabaseSetup.establish_provider_info_collection("16")

main()