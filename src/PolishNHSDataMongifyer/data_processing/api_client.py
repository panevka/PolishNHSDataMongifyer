
import traceback
import requests
from src.PolishNHSDataMongifyer.logging.logger import get_logger
logger = get_logger(__name__)

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
            logger.error(f"Unexpected error occurred: {str(e)}")
            logger.error(traceback.format_exc())

        
    def _encode_params(self, params):
        if params:
            from urllib.parse import urlencode
            return urlencode(params)
        return ""

NFZAPI_BASE_URL = "https://api.nfz.gov.pl/app-umw-api"
GEOAPIFY_BASE_URL = "https://api.geoapify.com/v1"