# AI Test Generator

**Automated Gherkin scenario generation using artificial intelligence**

An intelligent test automation tool that generates Gherkin scenarios for your Jira tasks using AI, then creates and links them automatically in Xray for seamless test management.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- **AI-Powered Generation**: Uses advanced language models (via Ollama) to generate contextual Gherkin scenarios
- **Jira Integration**: Automatically fetches tasks from Jira using customizable JQL queries
- **Xray Integration**: Creates test issues in Xray and links them back to original Jira tasks
- **Parallel Processing**: Multi-threaded execution for faster scenario generation
- **Smart Caching**: Caches generated scenarios to avoid redundant AI calls
- **Component Detection**: Intelligently identifies API components and generates relevant test scenarios
- **Comprehensive Logging**: Detailed logging with configurable levels and file output
- **Highly Configurable**: Extensive configuration options via environment variables

## Quick Start

### Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- Jira account with API access
- Xray Cloud subscription (or trial)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-test-generator.git
   cd ai-test-generator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Ollama model**
   ```bash
   # Install a reasoning model (recommended)
   ollama pull deepseek-r1:14b
   
   # Or use a smaller model for faster generation
   ollama pull qwen2.5:7b
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the generator**
   ```bash
   python -m src.ai_test_generator.main
   ```

## Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=DEMO

# Xray Configuration  
XRAY_CLIENT_ID=your-xray-client-id
XRAY_CLIENT_SECRET=your-xray-client-secret

# AI Model Configuration
AI_MODEL=deepseek-r1:14b

# JQL Query for task selection
JQL_QUERY=project = "{project_key}" AND Sprint in openSprints() AND labels = "automation-ready"
```

### Getting API Credentials

#### Jira API Token
1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Copy the token to `JIRA_API_TOKEN`

#### Xray Cloud Credentials
1. Go to Xray Cloud API credentials page
2. Create new API key pair
3. Copy Client ID and Client Secret to your `.env`

## Usage

### Basic Usage

```python
from ai_test_generator import AITestGenerator

# Initialize and run
generator = AITestGenerator()
generator.run()
```

### Custom JQL Query

```python
# Use custom query to select specific tasks
custom_query = 'project = "MYPROJECT" AND assignee = currentUser() AND labels = "ready-for-automation"'
generator.run(jql_query=custom_query)
```

### Programmatic Usage

```python
from ai_test_generator.generators import ScenarioGenerator
from ai_test_generator.managers import ResourceManager

# Generate a single scenario
resource_manager = ResourceManager()
scenario_generator = ScenarioGenerator(resource_manager)

scenario = scenario_generator.generate_gherkin(
    "As a user, I want to create a new account so that I can access the system"
)
print(scenario)
```

## Project Structure

```
ai-test-generator/
├── src/ai_test_generator/           # Main package
│   ├── clients/                     # API clients (Jira, Xray)
│   ├── config/                      # Configuration management
│   ├── generators/                  # AI scenario generators
│   ├── managers/                    # Resource managers
│   ├── utils/                       # Utilities (logging, cache)
│   └── main.py                      # Entry point
├── resources/                       # Example files and templates
│   ├── examples/                    # Gherkin examples and API schemas
│   └── templates/                   # Template files
├── tests/                           # Unit and integration tests
├── docs/                            # Documentation
└── scripts/                         # Setup and demo scripts
```

## AI Models

The tool supports various AI models through Ollama:

### Recommended Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `deepseek-r1:14b` | Large | Slow | Excellent | Production use |
| `deepseek-r1:8b` | Medium | Medium | Very Good | Balanced option |
| `qwen2.5:7b` | Small | Fast | Good | Development/testing |

### Model Installation

```bash
# Install your preferred model
ollama pull deepseek-r1:14b

# Verify installation
ollama list
```

## Example Output

The tool generates comprehensive Gherkin scenarios like this:

```gherkin
@TEST_DEMO-001
Scenario: @test=DEMO-001 Create new user account via REST API
  Given a clean test environment
  And valid user registration data:
    | field    | value              |
    | name     | John Doe           |
    | email    | john@example.com   |
    | username | johndoe123         |
  When a POST request is sent to "/users"
  Then http status matches 201
  And json path "id" exists and save with key "user_id"
  And json path "name" matches string "John Doe"
  And json path "email" matches string "john@example.com"
  And json path "created_at" exists
```

## Advanced Configuration

### Custom Component Detection

Add your own API components by modifying the `identify_api_component` method:

```python
component_keywords = {
    "your-api": ["keyword1", "keyword2", "specific-term"],
    "another-api": ["different", "keywords"]
}
```

### Cache Management

```python
from ai_test_generator.utils import CacheManager

cache = CacheManager()

# Get cache statistics
stats = cache.get_cache_stats()
print(f"Cache files: {stats['file_count']}")

# Clear old cache files
deleted = cache.cleanup_old_files(max_age_hours=24)
print(f"Deleted {deleted} old files")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ai_test_generator

# Run specific test file
pytest tests/test_scenario_generator.py -v
```

## Monitoring and Logging

The tool provides comprehensive logging:

```
2024-01-15 10:30:15 - ai_test_generator.AITestGenerator - INFO - Starting AI test generation process...
2024-01-15 10:30:16 - ai_test_generator.JiraClient - INFO - Retrieved 5 tasks from Jira
2024-01-15 10:30:45 - ai_test_generator.ScenarioGenerator - INFO - Generated scenario for DEMO-123
2024-01-15 10:31:20 - ai_test_generator.XrayClient - INFO - Created test DEMO-T001 for task DEMO-123
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/yourusername/ai-test-generator.git
cd ai-test-generator
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black src/ tests/
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [Usage Examples](docs/usage.md)
- [API Reference](docs/api_reference.md)

## Troubleshooting

### Common Issues

**Ollama Connection Error**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

**Jira Authentication Failed**
- Verify your email and API token
- Check if your Jira URL is correct
- Ensure your account has necessary permissions

**Xray Integration Issues**
- Verify Xray Cloud credentials
- Check if your Jira project has Xray enabled
- Ensure sufficient Xray Cloud quota

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.