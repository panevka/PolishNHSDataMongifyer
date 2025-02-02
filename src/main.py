import os
from src.PolishNHSDataMongifyer.collection_setup.db_setup import DatabaseSetup
from src.PolishNHSDataMongifyer.data_models.custom_models import DBSetupConfig
from src.PolishNHSDataMongifyer.data_processing.file_manager import FileDataManagement
from src.PolishNHSDataMongifyer.data_processing.processor import HealthcareDataProcessing
from src.PolishNHSDataMongifyer.user_handling.console import Console
from src.PolishNHSDataMongifyer.validation.validation import Validation


if __name__ == "__main__":
    current_folder = os.path.dirname(__file__)

    console = Console()
    configs = console.display_menu()
    validated_configs = Validation.validate_list(configs, DBSetupConfig)

    for config in validated_configs:
        file_manager = FileDataManagement(config.branch, config.service_type, current_folder)
        processor = HealthcareDataProcessing(config.branch, config.service_type, file_manager)
        DatabaseSetup(config, processor)