"""
Xray API client for test creation and management
"""

import json
import time
import logging
import requests
from typing import Optional, Dict

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class XrayClient:
    """Cliente para interactuar con la API de Xray"""
    
    def __init__(self):
        self.settings = get_settings()
        self._token: Optional[str] = None
        self._ensure_token()
    
    def _ensure_token(self):
        """Asegura que tenemos un token válido, obteniendo uno nuevo si es necesario"""
        if self._token is None:
            self._token = self._get_token()
    
    def _get_token(self, max_retries: int = 3) -> Optional[str]:
        """Obtiene un token de autenticación de Xray Cloud"""
        headers = {"Content-Type": "application/json"}
        data = json.dumps({
            "client_id": self.settings.xray_jira_client_id,
            "client_secret": self.settings.xray_jira_client_secret
        })
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.settings.xray_url_auth, 
                    headers=headers, 
                    data=data,
                    timeout=self.settings.request_timeout
                )
                
                if response.status_code == 200:
                    logger.info("Xray token obtained successfully")
                    return response.text.replace('"', "")
                else:
                    logger.warning(f"Error retrieving Xray token: {response.status_code}. Attempt {attempt} of {max_retries}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Exception retrieving Xray token: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        
        logger.error("Failed to obtain Xray token after multiple attempts")
        return None
    
    def refresh_token(self) -> bool:
        """Refresca el token de Xray"""
        new_token = self._get_token()
        if new_token:
            self._token = new_token
            return True
        return False
    
    def get_job_status(self, job_id: str, max_retries: int = 3) -> Optional[Dict]:
        """Recupera el estado de un trabajo desde Xray Cloud con mejor manejo de errores"""
        self._ensure_token()
        
        url = f"{self.settings.xray_base_url}/import/test/bulk/{job_id}/status"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token}"
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.settings.request_timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (401, 403):
                    logger.warning(f"Authentication error checking job status. Refreshing token...")
                    if self.refresh_token() and attempt < max_retries:
                        # Actualizar headers con nuevo token y continuar
                        headers["Authorization"] = f"Bearer {self._token}"
                        continue
                else:
                    logger.warning(f"Error retrieving job status: {response.status_code} - {response.text}")
            
            except Exception as e:
                logger.error(f"Exception retrieving job status: {e}")
            
            # Solo esperar si vamos a hacer otro intento
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Backoff exponencial: 2s, 4s, 8s, ...
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to retrieve job status for jobId {job_id} after {max_retries} attempts")
        return None
    
    def create_test(self, test_name: str, scenario: str, max_retries: int = 3, backoff_factor: float = 1.5) -> Optional[str]:
        """Crea un test en Xray con lógica de reintentos robusta y mejor manejo de errores"""
        self._ensure_token()
        
        url = f"{self.settings.xray_base_url}/import/test/bulk"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}"
        }
        payload = [{
            "testtype": "Cucumber",
            "fields": {
                "summary": test_name,
                "project": {"key": self.settings.jira_project_key}
            },
            "gherkin_def": scenario
        }]
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Creating test '{test_name}' (attempt {attempt}/{max_retries})...")
                
                # Añadir timeout para evitar bloqueos
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.settings.request_timeout
                )
                
                if response.status_code in (200, 201):
                    result = response.json()
                    if "jobId" in result:
                        job_id = result["jobId"]
                        logger.info(f"Test issue creation initiated. JobId: {job_id}")
                        
                        # Esperar con backoff exponencial y mostrar progreso
                        wait_time = 5  # Segundos iniciales
                        for check_attempt in range(1, 4):  # Máximo 3 intentos de verificación
                            logger.info(f"Waiting {wait_time}s before checking job status...")
                            time.sleep(wait_time)
                            
                            status = self.get_job_status(job_id, max_retries=2)
                            if status and "result" in status and "issues" in status["result"]:
                                issues = status["result"]["issues"]
                                if len(issues) > 0 and "key" in issues[0]:
                                    test_key = issues[0]["key"]
                                    logger.info(f"✅ Test issue created successfully with key: {test_key}")
                                    return test_key
                            
                            # Espera exponencial para el siguiente intento
                            wait_time = int(wait_time * backoff_factor)
                        
                        logger.warning(f"⚠️ Test creation still pending after multiple checks. JobId: {job_id}")
                        return None
                    else:
                        logger.warning(f"⚠️ No jobId returned. Response: {result}")
                else:
                    # Si es error 401/403, posiblemente expiró el token
                    if response.status_code in (401, 403):
                        logger.warning("⚠️ Authentication error. Refreshing Xray token...")
                        self.refresh_token()
                        # Actualizar headers
                        headers["Authorization"] = f"Bearer {self._token}"
                    else:
                        logger.warning(f"⚠️ Error: {response.status_code} - {response.text}")
                    
                    # Espera exponencial entre reintentos
                    if attempt < max_retries:
                        wait_time = backoff_factor ** attempt
                        logger.info(f"Waiting {wait_time:.2f}s before retry...")
                        time.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"❌ Exception in create_xray_test: {e}")
                if attempt < max_retries:
                    wait_time = backoff_factor ** attempt
                    logger.info(f"Waiting {wait_time:.2f}s before retry...")
                    time.sleep(wait_time)
        
        logger.error(f"❌ Failed to create test '{test_name}' after {max_retries} attempts")
        return None
    
    def is_token_valid(self) -> bool:
        """Verifica si el token actual es válido"""
        if not self._token:
            return False
        
        # Realizar una prueba simple para verificar el token
        url = f"{self.settings.xray_base_url}/tests"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code != 401
        except Exception:
            return False
