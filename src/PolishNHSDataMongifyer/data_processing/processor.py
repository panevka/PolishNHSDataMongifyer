import json
import os
import traceback

from pydantic import ValidationError
from src.PolishNHSDataMongifyer.data_processing.file_manager import FileDataManagement
from src.PolishNHSDataMongifyer.data_models.geoapify_models import Response, Result
from src.PolishNHSDataMongifyer.data_models.nhs_api_models import Agreement, AgreementsPage, Branch, Provider, ProvidersPage, ServiceType
from src.PolishNHSDataMongifyer.validation.validation import Validation
from .api_client import APIClient, NFZAPI_BASE_URL, GEOAPIFY_BASE_URL
from src.PolishNHSDataMongifyer.logging.logger import get_logger
logger = get_logger(__name__)


class HealthcareDataProcessing:

    def __init__(self, branch: Branch, service: ServiceType, file_manager: FileDataManagement ):
        self.branch = branch
        self.service = service
        self.file_manager = file_manager
        self.file_manager.setup_file_structure()

    def has_next_page(agreements_page: AgreementsPage|ProvidersPage):
       return agreements_page.links is not None and agreements_page.links.next_page is not None

    def process_agreements(self, year=2025, limit=25, startPage=1):
        params = {
            "year": year,
            "branch": self.branch.value,
            "serviceType":self.service.value,
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
                self.file_manager.save_agreements_page(page_data=serialized_agreements, page_number=page_number,
                                            request_page_limit=limit)
                params["page"] += 1  
            except Exception as e:
                logger.error(f"Unexpected error occurred while processing agreements: {str(e)}")
                logger.error(traceback.format_exc())

    def get_provider_info(self, provider_code: str) -> Provider:
        params = {
            "code": provider_code,
            "branch": str(self.branch.value),
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
            logger.error(f"Unexpected error occurred: {str(e)}")
            logger.error(traceback.format_exc())

    def process_output_providers(self):
        agreements_path = self.file_manager.AGREEMENTS_DATA_DIR
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
                                self.file_manager.save_provider(provider_data)
                                processed_providers.append(provider_data.attributes.code)
        except Exception as e:
            logger.error(f"Unexpected error occurred while processing providers: {str(e)}")
            logger.error(traceback.format_exc())

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
            logger.error(f"Unexpected error occurred while fetching provider geographical data: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def process_provider_geographical_data(self):
        input_file = self.file_manager.PROVIDERS_DATA
        with open(input_file, "r") as file:
            try:
                data = json.load(file)
                providers = Validation.validate_list(data, Provider)
                for provider in providers:
                    try:
                        geo_data = HealthcareDataProcessing.get_provider_geographical_data(provider)
                        geo_result = Validation.validate(geo_data, Result)
                        self.file_manager.save_provider_geo_data(provider, geo_result)
                    except Exception as e:
                        logger.error(f"Error while processing geographical data of providers: {str(e)}")
                        logger.error(traceback.format_exc())

            except ValidationError as e:
                logger.error(f"Cannot validate providers in {input_file}: {str(e)}")
                logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Unexpected error occurred while processing geographical data of providers: {str(e)}")
                logger.error(traceback.format_exc())