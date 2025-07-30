"""
AI-powered Gherkin scenario generator
"""

import os
import re
import functools
import logging
import ollama
from typing import List

from ..config.settings import get_settings
from ..managers.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class ScenarioGenerator:
    """Genera escenarios Gherkin utilizando IA"""
    
    def __init__(self, resource_manager: ResourceManager):
        self.settings = get_settings()
        self.resource_manager = resource_manager
    
    def extract_think_tags(self, text: str) -> List[str]:
        """Extrae y devuelve una lista con el contenido entre etiquetas <think> y </think>"""
        matches = re.findall(r'<think>(.*?)</think>', text, flags=re.DOTALL)
        return [match.strip() for match in matches]
    
    def remove_think_tags(self, text: str) -> str:
        """Elimina el contenido entre etiquetas <think> y </think>, incluyendo las propias etiquetas"""
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return cleaned_text.strip()
    
    def identify_api_component(self, user_story: str) -> str:
        """
        Identifica a qué componente API está relacionada la historia de usuario.
        Retorna: 'user-service', 'order-service', 'payment-service', o 'notification-service'
        """
        story_lower = user_story.lower()
        
        component_keywords = {
            "user-service": ["user", "account", "profile", "authentication", "login", "registration"],
            "order-service": ["order", "purchase", "cart", "checkout", "product", "inventory"],
            "payment-service": ["payment", "billing", "invoice", "transaction", "credit card", "paypal"],
            "notification-service": ["notification", "email", "sms", "alert", "message", "reminder"]
        }
        
        for component, keywords in component_keywords.items():
            if any(keyword in story_lower for keyword in keywords):
                return component
        
        # Default to user-service if no specific component is identified
        return "user-service"
    
    def get_component_context(self, component: str) -> str:
        """
        Retorna información de contexto específica para el componente identificado,
        incluyendo información relevante del esquema OpenAPI si está disponible.
        """
        contexts = {
            "user-service": (
                "The User Service manages user accounts, authentication, and profiles via REST API. "
                "Operations include user registration, login, profile updates, and account management. "
                "Test cases typically include user creation, authentication flows, profile operations, and user deletion."
            ),
            "order-service": (
                "The Order Service handles order processing, cart management, and inventory operations. "
                "Test cases typically verify order creation, status updates, product management, and inventory tracking."
            ),
            "payment-service": (
                "The Payment Service processes payments, manages billing, and handles transactions. "
                "Test cases include payment processing, invoice generation, refunds, and payment method validation."
            ),
            "notification-service": (
                "The Notification Service manages email, SMS, and push notifications. "
                "Test cases verify notification delivery, template processing, and communication preferences."
            )
        }
        
        # Añadir información de OpenAPI si está disponible
        api_context = ""
        if component == "user-service":
            schema = self.resource_manager.get_openapi_user_service_schema()
            if schema:
                paths = schema.get("paths", {})
                api_context = "\nKey endpoints:\n"
                for path, operations in list(paths.items())[:5]:  # Limitar a 5 endpoints
                    api_context += f"- {path}: "
                    methods = [m.upper() for m in operations.keys() if m in ["get", "post", "put", "delete"]]
                    api_context += f"{', '.join(methods)}\n"
        
        elif component == "order-service":
            schema = self.resource_manager.get_openapi_order_service_schema()
            if schema:
                paths = schema.get("paths", {})
                api_context = "\nKey endpoints:\n"
                for path, operations in list(paths.items())[:5]:  # Limitar a 5 endpoints
                    api_context += f"- {path}: "
                    methods = [m.upper() for m in operations.keys() if m in ["get", "post", "put", "delete"]]
                    api_context += f"{', '.join(methods)}\n"
        
        return contexts.get(component, "Component information not available.") + api_context
    
    def get_relevant_examples(self, task_description: str, examples_text: str) -> str:
        """
        Selecciona 1-2 ejemplos relevantes basados en palabras clave en la descripción de la tarea,
        teniendo en cuenta tanto el tipo de operación como el componente.
        """
        # Component keywords
        components = {
            "user-service": ["user", "account", "profile", "authentication", "login"],
            "order-service": ["order", "purchase", "cart", "product", "inventory"],
            "payment-service": ["payment", "billing", "transaction", "invoice"],
            "notification-service": ["notification", "email", "sms", "message"]
        }
        
        # Operation keywords
        operations = {
            "create": ["create", "add", "register", "new", "post"],
            "read": ["get", "read", "view", "fetch", "retrieve", "list"],
            "update": ["update", "edit", "modify", "change", "put", "patch"],
            "delete": ["delete", "remove", "deactivate", "cancel"],
            "search": ["search", "find", "filter", "query"],
            "validate": ["validate", "verify", "check", "confirm"]
        }
        
        # Find matching component and operation
        task_lower = task_description.lower()
        matched_components = []
        matched_operations = []
        
        for component, terms in components.items():
            if any(term in task_lower for term in terms):
                matched_components.append(component)
        
        for operation, terms in operations.items():
            if any(term in task_lower for term in terms):
                matched_operations.append(operation)
        
        # Default if no matches found
        if not matched_components:
            matched_components = ["user-service"]
        if not matched_operations:
            matched_operations = ["create", "read"]
        
        # Divide examples and select the relevant ones
        all_examples = re.findall(r'@TEST_\w+-\d+.*?(?=@TEST_\w+-\d+|$)', examples_text, re.DOTALL)
        
        selected_examples = []
        # First priority: match both component and operation
        for example in all_examples:
            example_lower = example.lower()
            if (any(component in example_lower for component in matched_components) and 
                any(operation in example_lower for operation in matched_operations)):
                selected_examples.append(example.strip())
                if len(selected_examples) >= 2:
                    break
        
        # Second priority: match component only
        if len(selected_examples) < 2:
            for example in all_examples:
                example_lower = example.lower()
                if any(component in example_lower for component in matched_components):
                    if example.strip() not in selected_examples:
                        selected_examples.append(example.strip())
                        if len(selected_examples) >= 2:
                            break
        
        # Third priority: match operation only
        if len(selected_examples) < 2:
            for example in all_examples:
                example_lower = example.lower()
                if any(operation in example_lower for operation in matched_operations):
                    if example.strip() not in selected_examples:
                        selected_examples.append(example.strip())
                        if len(selected_examples) >= 2:
                            break
        
        # If still no examples, use the first available
        if not selected_examples and all_examples:
            selected_examples.append(all_examples[0].strip())
        
        return "\n\n".join(selected_examples)
    
    @staticmethod
    def cache_result(func):
        """Decorator para implementar caché de escenarios generados"""
        @functools.wraps(func)
        def wrapper(self, user_story):
            # Generar un ID único basado en el contenido de la historia de usuario
            cache_id = str(hash(user_story))
            cache_file = os.path.join(self.settings.cache_dir, f"{cache_id}.txt")
            
            # Comprobar si ya existe en caché
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    logger.info(f"[CACHE HIT] Using cached scenario for: {user_story[:30]}...")
                    return f.read()
            
            # Generar nuevo escenario
            result = func(self, user_story)
            
            # Guardar en caché
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            return result
        return wrapper
    
    @cache_result
    def generate_gherkin(self, user_story: str) -> str:
        """
        Genera un escenario Gherkin único utilizando el modelo de IA configurado a través de Ollama.
        El prompt está optimizado para APIs REST genéricas y microservicios.
        """
        # Identify the component based on the user story
        component = self.identify_api_component(user_story)
        
        # Load gherkin examples
        examples_text = self.resource_manager.load_gherkin_examples()
        
        # Select relevant examples based on the user story and component
        relevant_examples = self.get_relevant_examples(user_story, examples_text)
        
        # Create component-specific context
        component_context = self.get_component_context(component)
        
        prompt = (
            f"As a QA Engineer with expertise in REST API testing, create a precise Gherkin scenario for the following Jira task. "
            f"The scenario must conform to specific format requirements.\n\n"
            
            f"### TASK CONTEXT ###\n"
            f"Jira task: \"{user_story}\"\n\n"
            
            f"### SYSTEM COMPONENTS OVERVIEW ###\n"
            f"{component_context}\n\n"
            
            f"### FORMAT REQUIREMENTS ###\n"
            f"1. First line must be a tag in format: \"@TEST_{self.settings.jira_project_key}-<ID>\" with a unique ID you generate\n"
            f"2. Second line must be: \"Scenario: @test={self.settings.jira_project_key}-<ID> <brief_descriptive_title>\" using the same ID\n"
            f"3. Structure the steps with Given/When/Then/And keywords\n\n"
            
            f"### TEST QUALITY GUIDELINES ###\n"
            f"- Create atomic tests (testing one specific functionality)\n"
            f"- Include specific validations for REST APIs: HTTP status codes, JSON structure, field values\n"
            f"- For persistence operations, verify changes were successfully applied\n"
            f"- For async operations, include verification steps for completion\n"
            f"- When appropriate, save IDs or tokens with \"exists and save\" steps for later use\n"
            f"- Always include cleanup steps for operations that create resources\n\n"
            
            f"### SCENARIO STRUCTURE TEMPLATE ###\n"
            f"@TEST_{self.settings.jira_project_key}-<ID>\n"
            f"Scenario: @test={self.settings.jira_project_key}-<ID> <verb>_<resource>_<condition>\n"
            f"  Given <environment_and_data_setup>\n"
            f"  When <main_action>\n"
            f"  Then <primary_verification>\n"
            f"  And <additional_verifications>\n\n"
            
            f"### RELEVANT EXAMPLES ###\n"
            f"{relevant_examples}\n\n"
            
            f"### FINAL INSTRUCTIONS ###\n"
            f"1. Carefully analyze the Jira task description\n"
            f"2. Identify which API component is being tested (user-service, order-service, payment-service, or notification-service)\n"
            f"3. Create the appropriate test scenario based on the component\n"
            f"4. Include only the Gherkin scenario in your response, no explanations\n"
        )
        
        try:
            response = ollama.chat(model=self.settings.ai_model, messages=[{"role": "user", "content": prompt}])
            if "message" in response:
                msg = response["message"]
                content = msg.content if hasattr(msg, "content") else str(msg)
                # Extract and display <think> content
                think_content = self.extract_think_tags(content)
                if think_content:
                    for item in think_content:
                        logger.info(f"Content in <think> tags: {item}")
                # Clean content by removing <think></think> sections
                cleaned_content = self.remove_think_tags(content)
                return cleaned_content
            else:
                logger.error("Error in Ollama response format")
                return "Error generating scenario."
        except Exception as e:
            logger.error(f"Exception while generating scenario: {e}")
            return f"Exception while generating scenario: {e}"
