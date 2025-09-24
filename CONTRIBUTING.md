# Contributing to Pyserv 

Thank you for your interest in contributing to Pyserv ! We welcome contributions from the community.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- C/C++ compiler (for building extensions)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ancillary-ai/pyserv .git
cd pyserv 
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### 1. Choose an Issue

- Check the [Issues](https://github.com/ancillary-ai/pyserv /issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write clear, concise commit messages
- Follow the existing code style
- Add tests for new features
- Update documentation as needed

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest --cov=pyserv  --cov-report=html

# Run linting
tox -e lint

# Run type checking
tox -e typecheck
```

### 5. Update Documentation

- Update docstrings for any modified functions/classes
- Add examples for new features
- Update the changelog

### 6. Submit a Pull Request

1. Ensure all tests pass
2. Update the changelog
3. Push your branch to GitHub
4. Create a pull request with a clear description
5. Link to any relevant issues

## Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks

All of these run automatically via pre-commit hooks.

## Testing

### Unit Tests

- Place in `tests/unit/`
- Test individual functions/classes
- Mock external dependencies

### Integration Tests

- Place in `tests/integration/`
- Test component interactions
- May require external services (use containers)

### System Tests

- Place in `tests/system/`
- Test end-to-end functionality
- May be slower and require full setup

### Performance Tests

- Place in `tests/performance/`
- Benchmark critical paths
- Compare against baselines

## Documentation

### Code Documentation

- Use Google-style docstrings
- Document all public APIs
- Include type hints

### User Documentation

- Update relevant guides in `docs/`
- Add examples in `examples/`
- Update README.md if needed

## Security

- Be aware of security implications
- Follow secure coding practices
- Report security issues privately
- See SECURITY.md for details

## Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

## Release Process

1. Update version in `src/pyserv/__init__.py`
2. Update CHANGELOG.md
3. Create a release PR
4. Tag the release after merge
5. PyPI publishing happens automatically via CI/CD

## Getting Help

- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Join our community chat

## License

By contributing to Pyserv , you agree that your contributions will be licensed under the MIT License.




