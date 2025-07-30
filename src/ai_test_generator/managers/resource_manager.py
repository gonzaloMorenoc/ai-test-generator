"""
Resource manager for loading external resources like Gherkin examples and OpenAPI schemas
"""

import os
import threading
import logging
import yaml
from typing import Dict, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ResourceManager:
    """Gestiona la carga de recursos externos como ejemplos y esquemas OpenAPI"""
    
    def __init__(self):
        self.settings = get_settings()
        self._openapi_lock = threading.Lock()
        self._openapi_user_service_schema: Optional[dict] = None
        self._openapi_order_service_schema: Optional[dict] = None
        self._gherkin_examples: Optional[str] = None
        
        # Crear directorio cache si no existe
        os.makedirs(self.settings.cache_dir, exist_ok=True)
    
    def load_gherkin_examples(self) -> str:
        """Carga ejemplos de escenarios Gherkin desde un archivo"""
        if self._gherkin_examples is not None:
            return self._gherkin_examples
            
        try:
            with open(self.settings.gherkin_examples_file, 'r', encoding='utf-8') as file:
                self._gherkin_examples = file.read()
            logger.info(f"Loaded {len(self._gherkin_examples.splitlines())} lines of Gherkin examples")
            return self._gherkin_examples
        except FileNotFoundError:
            logger.warning(f"Gherkin examples file not found: {self.settings.gherkin_examples_file}")
            return self._get_default_gherkin_example()
        except Exception as e:
            logger.error(f"Error loading Gherkin examples: {e}")
            return self._get_default_gherkin_example()
    
    def _get_default_gherkin_example(self) -> str:
        """Retorna un ejemplo Gherkin por defecto si no se puede cargar el archivo"""
        return '''Example of a simple scenario:
            @TEST_DEMO-001
            Scenario: @test=DEMO-001 Create new user account
            Given a valid user registration payload
            And the email "john@example.com" is not already registered
            When a POST request is sent to "/api/users"
            Then http status matches 201
            And json path "id" exists and save with key "user_id"
            And json path "email" matches string "john@example.com"
            And json path "status" matches string "active"
            '''
    
    def get_openapi_user_service_schema(self) -> Dict:
        """Carga el esquema OpenAPI para User Service de forma thread-safe"""
        with self._openapi_lock:
            if self._openapi_user_service_schema is None:
                self._openapi_user_service_schema = self._load_openapi_schema(self.settings.openapi_user_service_file)
            return self._openapi_user_service_schema
    
    def get_openapi_order_service_schema(self) -> Dict:
        """Carga el esquema OpenAPI para Order Service de forma thread-safe"""
        with self._openapi_lock:
            if self._openapi_order_service_schema is None:
                self._openapi_order_service_schema = self._load_openapi_schema(self.settings.openapi_order_service_file)
            return self._openapi_order_service_schema
    
    def _load_openapi_schema(self, file_path: str) -> Dict:
        """Carga un esquema OpenAPI desde un archivo YAML"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                schema = yaml.safe_load(file)
            logger.info(f"Loaded OpenAPI schema from {file_path}")
            return schema
        except FileNotFoundError:
            logger.warning(f"OpenAPI schema file not found: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading OpenAPI schema from {file_path}: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Limpia el cache de recursos cargados"""
        self._openapi_user_service_schema = None
        self._openapi_order_service_schema = None
        self._gherkin_examples = None
        logger.info("Resource cache cleared")
