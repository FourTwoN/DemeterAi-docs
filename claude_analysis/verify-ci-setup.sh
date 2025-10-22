#!/bin/bash
# Verification script for CI/CD setup
# DemeterAI v2.0 - Sprint 5

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Verifying CI/CD Setup - DemeterAI v2.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python version
echo "📌 Checking Python version..."
python3 --version | grep -q "3.12" && echo "  ✅ Python 3.12 detected" || echo "  ⚠️  Python 3.12 required"
echo ""

# Check workflow files
echo "📌 Checking workflow files..."
for file in .github/workflows/ci.yml .github/workflows/docker-build.yml .github/workflows/security.yml; do
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
        # Validate YAML syntax
        python3 -c "import yaml; yaml.safe_load(open('$file'))" && echo "     ✅ Valid YAML" || echo "     ❌ Invalid YAML"
    else
        echo "  ❌ $file missing"
    fi
done
echo ""

# Check pre-commit config
echo "📌 Checking pre-commit configuration..."
if [ -f ".pre-commit-config.yaml" ]; then
    echo "  ✅ .pre-commit-config.yaml exists"
    python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && echo "     ✅ Valid YAML" || echo "     ❌ Invalid YAML"
else
    echo "  ❌ .pre-commit-config.yaml missing"
fi
echo ""

# Check requirements-dev.txt
echo "📌 Checking development dependencies..."
if [ -f "requirements-dev.txt" ]; then
    echo "  ✅ requirements-dev.txt exists"

    # Check for essential tools
    for tool in ruff black isort mypy bandit safety pip-audit pytest pre-commit; do
        grep -q "$tool" requirements-dev.txt && echo "     ✅ $tool" || echo "     ⚠️  $tool not found"
    done
else
    echo "  ❌ requirements-dev.txt missing"
fi
echo ""

# Check if pre-commit is installed
echo "📌 Checking pre-commit installation..."
if command -v pre-commit &> /dev/null; then
    echo "  ✅ pre-commit is installed"
    pre-commit --version
else
    echo "  ⚠️  pre-commit not installed (run: pip install pre-commit)"
fi
echo ""

# Check if hooks are installed
echo "📌 Checking pre-commit hooks..."
if [ -f ".git/hooks/pre-commit" ]; then
    echo "  ✅ Pre-commit hooks are installed"
else
    echo "  ⚠️  Pre-commit hooks not installed (run: pre-commit install)"
fi
echo ""

# Check documentation
echo "📌 Checking documentation..."
for doc in .github/workflows/README.md .github/DEVELOPMENT.md .github/CI_CD_SUMMARY.md .github/QUICK_REFERENCE.md; do
    if [ -f "$doc" ]; then
        echo "  ✅ $doc exists"
    else
        echo "  ⚠️  $doc missing"
    fi
done
echo ""

# Check Docker
echo "📌 Checking Docker..."
if command -v docker &> /dev/null; then
    echo "  ✅ Docker is installed"
    docker --version
else
    echo "  ⚠️  Docker not installed"
fi
echo ""

# Check Docker Compose
echo "📌 Checking Docker Compose..."
if command -v docker compose &> /dev/null; then
    echo "  ✅ Docker Compose is installed"
    docker compose version
else
    echo "  ⚠️  Docker Compose not installed"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Verification Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next Steps:"
echo "  1. Install dependencies: pip install -r requirements-dev.txt"
echo "  2. Install pre-commit hooks: pre-commit install"
echo "  3. Run pre-commit: pre-commit run --all-files"
echo "  4. Test locally: pytest tests/ --cov=app"
echo "  5. Push to GitHub and verify CI runs"
echo ""
echo "📚 Documentation:"
echo "  - Workflows: .github/workflows/README.md"
echo "  - Setup: .github/DEVELOPMENT.md"
echo "  - Quick Ref: .github/QUICK_REFERENCE.md"
echo ""
