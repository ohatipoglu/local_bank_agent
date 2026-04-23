# Contributing to Local Bank AI Agent

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
4. **Set up development environment** (see below)
5. **Make your changes**
6. **Write tests** for new functionality
7. **Run tests and linting** (see below)
8. **Commit changes** (`git commit -m 'Add amazing feature'`)
9. **Push to your fork** (`git push origin feature/amazing-feature`)
10. **Open a Pull Request**

## 🛠️ Development Environment Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Setup Commands
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/local-bank-ai-agent.git
cd local-bank-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install with development dependencies
make dev-install
# or manually:
pip install -e ".[dev]"
pre-commit install

# Run tests to verify setup
make test
```

## 📝 Code Standards

### Code Style
We use automated tools to maintain code quality:

- **Ruff**: Fast linter (replaces flake8, isort, etc.)
- **Black**: Code formatter
- **MyPy**: Static type checker

### Running Quality Checks
```bash
# Lint code
make lint

# Auto-fix lint issues
make lint-fix

# Format code
make format

# Type check
make type-check

# Run all checks
make check
```

### Pre-commit Hooks
We use pre-commit hooks to automatically check code before commits:

```bash
# Install hooks
make pre-commit

# Run on all files
make hooks
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_config.py -v

# Run only unit tests (skip slow tests)
pytest -m "not slow"
```

### Writing Tests
- Place tests in the `tests/` directory
- Name test files: `test_<module_name>.py`
- Use descriptive test function names: `test_<what_youre_testing>`
- Include both positive and negative test cases
- Use fixtures for common test data

Example:
```python
def test_sanitize_filename_removes_path_separators():
    """Test that path separators are removed from filenames."""
    assert sanitize_filename("../../etc/passwd") == "etcpasswd"
    assert sanitize_filename("..\\..\\windows") == "windows"
```

## 🏗️ Architecture Guidelines

### Clean Architecture Layers
Follow the established layering:
1. **Presentation** (web_server.py, templates/)
2. **Application** (LangChain agent, tools)
3. **Domain** (entities, interfaces)
4. **Infrastructure** (implementations, external services)

### Adding New Features

#### New Banking Tool
1. Add method to `IAccountService` interface
2. Implement in `MockAccountService`
3. Add tool in `BankToolsRegistry`
4. Write tests

#### New TTS Engine
1. Create engine class in `infrastructure/tts_engine.py`
2. Implement required interface methods
3. Add to `TTSEngineRouter`
4. Write tests

#### Configuration Changes
1. Add to `Settings` class in `core/config.py`
2. Update `.env.example`
3. Add validation if needed
4. Update documentation

## 📋 Pull Request Guidelines

### Before Submitting
- [ ] Code follows style guidelines (run `make check`)
- [ ] All tests pass (`make test`)
- [ ] Coverage hasn't decreased significantly
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and descriptive

### PR Description
Include:
1. **What** changed and **why**
2. **How** to test the changes
3. Any **breaking changes**
4. Screenshots for UI changes

### Commit Messages
Follow conventional commits:
```
feat: add credit card payment tool
fix: sanitize filenames in audio upload
docs: update setup instructions
test: add config validation tests
refactor: extract TTS engine interface
```

## 🎯 Areas Needing Contribution

### High Priority
- [ ] Redis session storage implementation
- [ ] Database-backed mock services
- [ ] OpenTelemetry integration
- [ ] Kubernetes manifests
- [ ] API versioning (/api/v1/)

### Medium Priority
- [ ] Multi-language support (i18n)
- [ ] Conversation export functionality
- [ ] User feedback mechanism
- [ ] Performance benchmarks
- [ ] Load testing scripts

### Good First Issues
- [ ] Additional test coverage
- [ ] Documentation improvements
- [ ] Code refactoring for clarity
- [ ] Bug fixes (see Issues tab)

## 🐛 Reporting Issues

### Bug Reports
Include:
1. **Description**: What happened vs. what should happen
2. **Steps to reproduce**
3. **Environment**: OS, Python version, etc.
4. **Logs/Errors**: Relevant output
5. **Screenshots** if applicable

### Feature Requests
Include:
1. **Problem** you're trying to solve
2. **Proposed solution**
3. **Alternatives** considered
4. **Additional context**

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## 💬 Getting Help

- Open a GitHub Issue
- Join discussions in Pull Requests
- Check existing documentation

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Local Bank AI Agent! 🎉
