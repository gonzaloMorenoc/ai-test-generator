#!/bin/bash

# AI Test Generator - Automated Installation Script
# This script sets up the complete development environment automatically

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_MIN_VERSION="3.8"
PROJECT_NAME="ai-test-generator"
REPO_URL="https://github.com/yourusername/ai-test-generator.git"

# Print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo ""
    print_color $BLUE "=============================================="
    print_color $BLUE "$1"
    print_color $BLUE "=============================================="
    echo ""
}

print_success() {
    print_color $GREEN "✅ $1"
}

print_warning() {
    print_color $YELLOW "⚠️  $1"
}

print_error() {
    print_color $RED "❌ $1"
}

print_info() {
    print_color $BLUE "ℹ️  $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "Python $PYTHON_VERSION is compatible"
            return 0
        else
            print_error "Python $PYTHON_VERSION found, but $PYTHON_MIN_VERSION+ required"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Install system dependencies
install_system_deps() {
    print_info "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv git curl build-essential
        elif command_exists yum; then
            sudo yum install -y python3 python3-pip git curl gcc gcc-c++ make
        elif command_exists pacman; then
            sudo pacman -S python python-pip git curl base-devel
        else
            print_warning "Unsupported Linux distribution. Please install Python 3.8+, pip, git, and curl manually."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install python@3.11 git curl
        else
            print_warning "Homebrew not found. Please install Python 3.8+, git, and curl manually."
            print_info "You can install Homebrew from: https://brew.sh/"
        fi
    else
        print_warning "Unsupported operating system: $OSTYPE"
        print_info "Please install Python 3.8+, pip, git, and curl manually."
    fi
}

# Install Ollama
install_ollama() {
    print_info "Installing Ollama..."
    
    if command_exists ollama; then
        print_success "Ollama already installed"
        return 0
    fi
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            brew install ollama
        else
            print_warning "Please install Ollama manually from: https://ollama.ai/download"
            return 1
        fi
    else
        print_warning "Please install Ollama manually from: https://ollama.ai/download"
        return 1
    fi
    
    if command_exists ollama; then
        print_success "Ollama installed successfully"
    else
        print_error "Ollama installation failed"
        return 1
    fi
}

# Setup project
setup_project() {
    print_info "Setting up project directory..."
    
    if [ -d "$PROJECT_NAME" ]; then
        print_warning "Directory $PROJECT_NAME already exists"
        read -p "Do you want to remove it and start fresh? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_NAME"
        else
            print_info "Using existing directory"
            cd "$PROJECT_NAME"
            return 0
        fi
    fi
    
    # Check if we should clone or use current directory
    if [ "$(basename "$PWD")" = "$PROJECT_NAME" ] && [ -f "setup.py" ]; then
        print_info "Already in project directory"
    else
        print_info "Cloning repository..."
        git clone "$REPO_URL" "$PROJECT_NAME"
        cd "$PROJECT_NAME"
    fi
    
    print_success "Project directory ready"
}

# Setup Python virtual environment
setup_venv() {
    print_info "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists"
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."
    
    # Install the package in development mode
    pip install -e ".[dev,all]"
    
    print_success "Python dependencies installed"
}

# Setup pre-commit hooks
setup_precommit() {
    print_info "Setting up pre-commit hooks..."
    
    if command_exists pre-commit; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "Pre-commit not found, skipping hooks setup"
    fi
}

# Setup configuration
setup_config() {
    print_info "Setting up configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Configuration file created from template"
        print_warning "Please edit .env file with your actual credentials"
    else
        print_info "Configuration file already exists"
    fi
}

# Start Ollama and install model
setup_ollama_model() {
    print_info "Setting up Ollama model..."
    
    # Start Ollama in background
    if ! pgrep -f "ollama serve" > /dev/null; then
        print_info "Starting Ollama service..."
        ollama serve &
        OLLAMA_PID=$!
        sleep 5  # Wait for service to start
    else
        print_info "Ollama service already running"
    fi
    
    # Check if Ollama is responding
    if curl -s http://localhost:11434/api/version > /dev/null; then
        print_success "Ollama service is running"
        
        # Install default model
        print_info "Installing AI model (this may take a few minutes)..."
        ollama pull qwen2.5:7b
        print_success "AI model installed"
    else
        print_warning "Ollama service not responding, you may need to start it manually"
    fi
}

# Run tests
run_tests() {
    print_info "Running tests to verify installation..."
    
    # Run unit tests only (no external dependencies)
    if pytest tests/ -m "unit or not external" --tb=short -q; then
        print_success "Tests passed"
    else
        print_warning "Some tests failed, but installation may still be functional"
    fi
}

# Setup demo
setup_demo() {
    print_info "Setting up demo environment..."
    
    python scripts/setup_demo.py
    
    if [ -d "demo" ]; then
        print_success "Demo environment created"
        print_info "You can run the demo with: cd demo && python run_demo.py"
    else
        print_warning "Demo setup may have failed"
    fi
}

# Print final instructions
print_final_instructions() {
    print_header "Installation Complete!"
    
    echo "🎉 AI Test Generator has been successfully installed!"
    echo ""
    echo "📁 Project location: $(pwd)"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Activate virtual environment: source venv/bin/activate"
    echo "   2. Edit configuration: nano .env"
    echo "   3. Add your Jira and Xray credentials"
    echo "   4. Run demo: cd demo && python run_demo.py"
    echo "   5. Run on real data: ai-test-generator"
    echo ""
    echo "📚 Documentation:"
    echo "   - Installation: docs/installation.md"
    echo "   - Configuration: docs/configuration.md"
    echo "   - Usage: docs/usage.md"
    echo ""
    echo "🛠️  Development:"
    echo "   - Run tests: pytest"
    echo "   - Format code: black src/ tests/"
    echo "   - Check style: flake8 src/ tests/"
    echo ""
    echo "❓ Need help?"
    echo "   - GitHub Issues: https://github.com/yourusername/ai-test-generator/issues"
    echo "   - Documentation: https://github.com/yourusername/ai-test-generator/wiki"
    echo ""
}

# Main installation function
main() {
    print_header "AI Test Generator - Automated Installation"
    
    print_info "This script will install AI Test Generator and all dependencies"
    print_info "Operating System: $OSTYPE"
    echo ""
    
    # Check for non-interactive mode
    if [ "$1" = "--non-interactive" ]; then
        print_info "Running in non-interactive mode"
        INTERACTIVE=false
    else
        INTERACTIVE=true
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Installation cancelled"
            exit 0
        fi
    fi
    
    # Installation steps
    print_header "Step 1: System Dependencies"
    if ! check_python_version; then
        print_info "Installing system dependencies..."
        install_system_deps
        if ! check_python_version; then
            print_error "Python installation failed or version still incompatible"
            exit 1
        fi
    fi
    
    print_header "Step 2: Ollama Installation"
    install_ollama
    
    print_header "Step 3: Project Setup"
    setup_project
    
    print_header "Step 4: Python Environment"
    setup_venv
    
    print_header "Step 5: Dependencies"
    install_python_deps
    
    print_header "Step 6: Development Tools"
    setup_precommit
    
    print_header "Step 7: Configuration"
    setup_config
    
    print_header "Step 8: AI Model"
    setup_ollama_model
    
    print_header "Step 9: Demo Setup"
    setup_demo
    
    print_header "Step 10: Verification"
    run_tests
    
    print_final_instructions
}

# Handle script interruption
trap 'print_error "Installation interrupted"; exit 1' INT TERM

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root is not recommended"
    print_info "Consider running as a regular user"
fi

# Run main installation
main "$@"