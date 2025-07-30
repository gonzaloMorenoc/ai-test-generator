"""
Main AI Test Generator class that orchestrates the complete process
"""

import time
import logging
import concurrent.futures
from typing import Dict, List, Optional
from tqdm import tqdm

from .config.settings import get_settings
from .managers.resource_manager import ResourceManager
from .clients.jira_client import JiraClient
from .clients.xray_client import XrayClient
from .generators.scenario_generator import ScenarioGenerator
from .utils.helpers import setup_logging, format_duration, validate_api_credentials

logger = logging.getLogger(__name__)


class AITestGenerator:
    """Main class that coordinates the scenario generation process"""
    
    def __init__(self, config_override: Optional[Dict] = None):
        """Initialize the AI Test Generator
        
        Args:
            config_override: Optional configuration overrides
        """
        # Setup logging first
        setup_logging()
        
        self.start_time = time.time()
        self.settings = get_settings()
        
        # Apply any configuration overrides
        if config_override:
            for key, value in config_override.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
        
        # Initialize components
        self.resource_manager = ResourceManager()
        self.jira_client = JiraClient()
        self.xray_client = XrayClient()
        self.scenario_generator = ScenarioGenerator(self.resource_manager)
        
        # Validate configuration
        self._validate_setup()
    
    def _validate_setup(self) -> None:
        """Validate the setup and configuration"""
        logger.info("🔧 Validating configuration...")
        
        # Check API credentials
        credentials = validate_api_credentials()
        missing_creds = [cred for cred, valid in credentials.items() if not valid]
        
        if missing_creds:
            logger.warning(f"⚠️ Missing API credentials: {', '.join(missing_creds)}")
            logger.warning("Please check your .env file or environment variables")
        
        # Check Ollama model
        try:
            import ollama
            models = ollama.list()
            model_names = [model['name'] for model in models.get('models', [])]
            
            if self.settings.ai_model not in model_names:
                logger.warning(f"⚠️ AI model '{self.settings.ai_model}' not found in Ollama")
                logger.warning(f"Available models: {', '.join(model_names)}")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify Ollama models: {e}")
        
        logger.info("✅ Configuration validation completed")
    
    def run(self, jql_query: Optional[str] = None) -> Dict:
        """Executes the complete test generation process and its integration with Jira/Xray
        
        Args:
            jql_query: Optional custom JQL query to override settings
            
        Returns:
            Dict with execution results and statistics
        """
        logger.info("🚀 Starting AI test generation process...")
        
        try:
            # 1. Get tasks from Jira
            tasks = self._get_tasks(jql_query)
            if not tasks:
                logger.error("❌ No tasks found to process")
                return {"success": False, "error": "No tasks found"}
            
            # 2. Generate test scenarios
            generated_tests = self._generate_scenarios(tasks)
            if not generated_tests:
                logger.error("❌ No scenarios could be generated")
                return {"success": False, "error": "No scenarios generated"}
            
            # 3. Create Xray test issues and link to Jira tasks
            xray_results = self._process_xray_tests(generated_tests)
            
            # 4. Show summary and return results
            summary = self._show_summary()
            
            return {
                "success": True,
                "tasks_processed": len(tasks),
                "scenarios_generated": len(generated_tests),
                "xray_tests_created": xray_results.get("created", 0),
                "jira_links_created": xray_results.get("linked", 0),
                "execution_time": summary["execution_time"],
                "jira_requests": summary["jira_requests"]
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in main execution: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _get_tasks(self, jql_query: Optional[str] = None) -> List[Dict]:
        """Gets tasks from Jira using the Jira client"""
        query = jql_query or self.settings.jql_query
        logger.info(f"📋 Retrieving tasks from Jira using query: {query}")
        return self.jira_client.get_sprint_tasks(query)
    
    def _generate_scenarios(self, tasks: List[Dict]) -> Dict[str, str]:
        """Generates scenarios for the provided tasks using AI"""
        logger.info(f"🧠 Generating scenarios for {len(tasks)} tasks...")
        generated_tests = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.settings.max_worker_threads) as executor:
            # Prepare arguments for each task
            futures = {}
            for task in tasks:
                key = task.get("key", "N/A")
                user_story = task.get("fields", {}).get("summary", "")
                if user_story:
                    future = executor.submit(self.scenario_generator.generate_gherkin, user_story)
                    futures[future] = key
            
            # Process results as they complete
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Generating scenarios"):
                key = futures[future]
                try:
                    scenario = future.result()
                    generated_tests[key] = scenario
                    
                    # Show result
                    logger.info("\n" + "=" * 50)
                    logger.info(f"📝 Generated scenario for {key}:")
                    logger.info("-" * 50)
                    logger.info(scenario)
                    logger.info("=" * 50 + "\n")
                except Exception as e:
                    logger.error(f"❌ Error generating scenario for {key}: {e}")
        
        return generated_tests
    
    def _process_xray_tests(self, generated_tests: Dict[str, str]) -> Dict:
        """Creates Xray tests and links them to Jira tasks"""
        created_xray_links = {}
        failed_creations = []
        
        # Split into batches for more efficient processing
        task_batches = [list(generated_tests.items())[i:i+self.settings.batch_size] 
                        for i in range(0, len(generated_tests), self.settings.batch_size)]
        
        logger.info(f"\n📦 Processing test creation in Xray in {len(task_batches)} batches...")
        
        for batch_idx, batch in enumerate(task_batches):
            logger.info(f"\n📦 Processing batch {batch_idx+1}/{len(task_batches)}")
            batch_results = {}
            batch_failures = []
            
            # Process each task in the batch
            for task_key, scenario in batch:
                test_name = f"Test for {task_key}"
                test_key = self.xray_client.create_test(test_name, scenario)
                
                if test_key:
                    batch_results[task_key] = test_key
                else:
                    batch_failures.append((task_key, scenario))
            
            # Pause between batches to avoid rate limits
            if batch_idx < len(task_batches) - 1:
                logger.info(f"⏸️ Pausing between batches (5s)...")
                time.sleep(5)
            
            # Update global results
            created_xray_links.update(batch_results)
            failed_creations.extend(batch_failures)
        
        # Retry creating failed tests (one more time)
        if failed_creations:
            logger.info(f"\n⚠️ Retrying {len(failed_creations)} failed test creations...")
            for task_key, scenario in failed_creations:
                test_name = f"Test for {task_key} (retry)"
                test_key = self.xray_client.create_test(test_name, scenario, max_retries=2)
                if test_key:
                    created_xray_links[task_key] = test_key
        
        # Link tests with Jira tasks
        successful_links = self._link_xray_tests(created_xray_links)
        
        return {
            "created": len(created_xray_links),
            "linked": successful_links
        }
    
    def _link_xray_tests(self, created_xray_links: Dict[str, str]) -> int:
        """Links the created Xray tests with Jira tasks"""
        if not created_xray_links:
            logger.warning("⚠️ No Xray tests to link")
            return 0
            
        logger.info(f"\n🔗 Linking {len(created_xray_links)} tests to Jira tasks...")
        successful_links = 0
        failed_links = []
        
        for task_key, test_key in created_xray_links.items():
            if self.jira_client.link_test_to_task(task_key, test_key):
                successful_links += 1
            else:
                failed_links.append((task_key, test_key))
        
        # Retry failed links
        if failed_links:
            logger.info(f"\n⚠️ Retrying {len(failed_links)} failed links...")
            for task_key, test_key in failed_links:
                if self.jira_client.link_test_to_task(task_key, test_key, max_retries=2):
                    successful_links += 1
        
        return successful_links
    
    def _show_summary(self) -> Dict:
        """Shows an execution summary"""
        end_time = time.time()
        elapsed_time = end_time - self.start_time
        
        logger.info(f"\n📊 EXECUTION SUMMARY:")
        logger.info(f"   - Total Jira requests: {self.jira_client.get_request_count()}")
        logger.info(f"   - Execution time: {format_duration(elapsed_time)}")
        logger.info(f"   - AI Model used: {self.settings.ai_model}")
        logger.info(f"   - Worker threads: {self.settings.max_worker_threads}")
        logger.info("✅ Process completed successfully!")
        
        return {
            "execution_time": elapsed_time,
            "jira_requests": self.jira_client.get_request_count()
        }
    
    def generate_single_scenario(self, user_story: str) -> str:
        """Generate a single scenario for testing purposes"""
        return self.scenario_generator.generate_gherkin(user_story)


def main():
    """Main function to execute from command line"""
    try:
        # Execute the test generator
        generator = AITestGenerator()
        result = generator.run()
        
        if result["success"]:
            logger.info("🎉 AI Test Generator completed successfully!")
            return 0
        else:
            logger.error(f"❌ AI Test Generator failed: {result.get('error', 'Unknown error')}")
            return 1
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in main execution: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
