from datetime import date, datetime
import traceback
from typing import Any, List, Type
from pydantic import BaseModel, TypeAdapter, ValidationError
from src.PolishNHSDataMongifyer.logging.logger import get_logger
logger = get_logger(__name__)

class Validation:
    @staticmethod
    def validate(variable: Any, model: Type[BaseModel]) -> BaseModel:
        try:
            return model(**variable) if isinstance(variable, dict) else model.model_validate(variable)
        except ValidationError as e:
            logger.error(f"Validation failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def validate_list(items: List[Any], model: Type[BaseModel]) -> List[BaseModel]:
        try:
            return TypeAdapter(List[model]).validate_python(items)
        except ValidationError as e:
            logger.error(f"Validation failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))
    