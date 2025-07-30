"""
Jira API client for task management and linking
"""

import base64
import time
import logging
import requests
from typing import List, Dict, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class JiraClient:
    """Cliente para interactuar con la API de Jira"""
    
    def __init__(self):
        self.settings = get_settings()
        self.auth_token = base64.b64encode(
            f"{self.settings.email}:{self.settings.jira_api_token}".encode()
        ).decode()
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {self.auth_token}"
        }
        self.request_count = 0
    
    def get_sprint_tasks(self, jql: Optional[str] = None, max_retries: int = 3) -> List[Dict]:
        """Recupera historias de usuario y tareas del sprint actual en Jira"""
        query = jql or self.settings.jql_query
        url = f"{self.settings.jira_url}/rest/api/3/search"
        params = {"jql": query, "maxResults": 50}
        
        for attempt in range(1, max_retries + 1):
            self.request_count += 1
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=self.settings.request_timeout
                )
                
                if response.status_code == 200:
                    issues = response.json().get("issues", [])
                    logger.info(f"✅ Retrieved {len(issues)} tasks from Jira")
                    return issues
                else:
                    logger.warning(f"Error retrieving sprint tasks: {response.status_code}. Attempt {attempt} of {max_retries}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)  # Backoff exponencial
            except Exception as e:
                logger.error(f"Exception retrieving sprint tasks: {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        
        logger.error("Failed to retrieve sprint tasks after multiple attempts")
        return []
    
    def link_test_to_task(self, task_key: str, test_key: str, max_retries: int = 3, backoff_factor: float = 1.5) -> bool:
        """Crea un enlace en Jira con lógica de reintentos robusta"""
        url = f"{self.settings.jira_url}/rest/api/3/issueLink"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_token}"
        }
        payload = {
            "type": {"name": "Test"},
            "inwardIssue": {"key": test_key},
            "outwardIssue": {"key": task_key}
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                self.request_count += 1
                logger.info(f"Linking test {test_key} to task {task_key} (attempt {attempt}/{max_retries})...")
                
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.settings.request_timeout
                )
                
                if response.status_code in (200, 201, 204):
                    logger.info(f"✅ Successfully linked test {test_key} to task {task_key}")
                    return True
                else:
                    logger.warning(f"⚠️ Error linking: {response.status_code} - {response.text}")
                    
                    # Espera exponencial entre reintentos
                    if attempt < max_retries:
                        wait_time = backoff_factor ** attempt
                        logger.info(f"Waiting {wait_time:.2f}s before retry...")
                        time.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"❌ Exception in link_test_to_task: {e}")
                if attempt < max_retries:
                    wait_time = backoff_factor ** attempt
                    logger.info(f"Waiting {wait_time:.2f}s before retry...")
                    time.sleep(wait_time)
        
        logger.error(f"❌ Failed to link test {test_key} to task {task_key} after {max_retries} attempts")
        return False
    
    def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Obtiene información detallada de una issue específica"""
        url = f"{self.settings.jira_url}/rest/api/3/issue/{issue_key}"
        
        try:
            self.request_count += 1
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.settings.request_timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error retrieving issue {issue_key}: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Exception retrieving issue {issue_key}: {e}")
            return None
    
    def get_request_count(self) -> int:
        """Retorna el número de requests realizados"""
        return self.request_count
