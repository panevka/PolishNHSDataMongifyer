import json
import os
import traceback
from typing import List

from pydantic import ValidationError

from src.PolishNHSDataMongifyer.data_models.custom_models import DBSetupConfig, ProviderGeoEntry
from src.PolishNHSDataMongifyer.data_models.mongodb_models import AgreementInfo, ProviderGeoData, ProviderInfo
from src.PolishNHSDataMongifyer.data_models.nhs_api_models import Agreement, Provider
from src.PolishNHSDataMongifyer.data_processing.file_manager import FileDataManagement
from src.PolishNHSDataMongifyer.data_processing.processor import HealthcareDataProcessing
from src.PolishNHSDataMongifyer.validation.validation import Validation
from src.PolishNHSDataMongifyer.logging.logger import get_logger
logger = get_logger(__name__)

class DatabaseSetup:                          
    def __init__(self, config: DBSetupConfig, data_processor: HealthcareDataProcessing):
            self.branch = config.branch.value
            self.NHS_processor = data_processor
            self.NHS_file_manager = self.NHS_processor.file_manager
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
            logger.error(f"Could not validate data of providers for branch {self.branch}: {str(e)}")
            logger.error(traceback.format_exc())


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
                                        logger.error(f"Error while ProviderInfo collection member in branch: {self.branch}: {str(e)}")
                                        logger.error(traceback.format_exc())

                                with open(collection_path, "w") as f:
                                    json.dump(collection_entries_list, f, indent=4)
                                    provider_file.seek(0)
                        except Exception as e:
                            logger.error(f"Error while creating agreements collection for branch: {self.branch}: {str(e)}")
                            logger.error(traceback.format_exc())

            except Exception as e:
                logger.error(f"Could not establish ProviderInfo collection for branch {self.branch}: {str(e)}")
                logger.error(traceback.format_exc())

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
                            logger.error(f"Couldn't create ProviderGeoCollection member for branch {self.branch}: {str(e)}")
                            logger.error(traceback.format_exc())
                        except json.JSONDecodeError:
                            logger.error(f"Couldn't create ProviderGeoCollection member for branch {self.branch}: {str(e)}")
            except ValidationError as e:
                logger.error(f"Could not validate data in {geodata_path}")
                logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Unexpected error occurred: {str(e)}")
                logger.error(traceback.format_exc())

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
                        logger.error(f"Could not create AgreementsCollection member: {str(e)}")
                        logger.error(traceback.format_exc())
                    except Exception as e:
                        logger.error(f"Could not write to agreements collection file: {str(e)}")
                        logger.error(traceback.format_exc())
