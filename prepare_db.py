import time
import json
import logging
import os
import traceback
from typing import Dict, List
from pydantic import TypeAdapter, parse_obj_as
import requests
import sys

sys.path.append('../PolishNHSDataMongifyer')
from data_models import Agreement, AgreementsData, AgreementsPage, Branch, Provider, ProvidersPage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

NFZAPI_BASE_URL = "https://api.nfz.gov.pl/app-umw-api"

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

            providers_list.append(provider_data.model_dump())
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
                serialized_agreements = [agreement.model_dump_json() for agreement in agreements]
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
        try:
            AgreementsList = TypeAdapter(List[Agreement])
            for page_file in os.listdir(branch_path):
                file_path = os.path.join(branch_path, page_file)
                with open(file_path, 'r') as json_file:
                    data = json.load(json_file)
                    agreements = AgreementsList.validate_python(data)
                    providers = [agreement.attributes.provider_code for agreement in agreements]
                    for provider_code in providers:
                        time.sleep(1.3)
                        provider_data = HealthcareDataProcessing.get_provider_info(provider_code, branch)
                        if(provider_data):
                            FileDataManagement.save_provider(provider_data, output_file)
        except Exception as e:
            logging.error(f"Unexpected error occurred: {str(e)}")
            logging.error(traceback.format_exc())

    
def main():
    HealthcareDataProcessing.process_agreements(branch="10")
    HealthcareDataProcessing.process_output_providers("10")

main()