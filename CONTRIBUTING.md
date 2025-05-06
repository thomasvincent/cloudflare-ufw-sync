# Contributing to Cloudflare UFW Sync

First of all, thank you for considering contributing to Cloudflare UFW Sync! This project aims to be a robust and reliable tool for system administrators, and your contributions help make that possible.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct. Please be respectful and considerate of others.

## How Can I Contribute?

### Reporting Bugs

Bug reports help us improve the project. When reporting a bug, please:

1. Check if the bug has already been reported in the GitHub Issues.
2. Use the bug report template when creating an issue.
3. Include as much information as possible:
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Error messages and logs
   - Environment details (OS, Python version, etc.)

### Suggesting Features

We love hearing about new features that would be useful. When suggesting a feature:

1. Check if the feature has already been suggested in the GitHub Issues.
2. Use the feature request template when creating an issue.
3. Clearly describe the feature and its use case.
4. Consider if the feature fits the scope and goals of the project.

### Pull Requests

1. Fork the repository and create your branch from `main`.
2. If you've added code, add tests that cover your changes.
3. Ensure the test suite passes by running `pytest`.
4. Make sure your code follows the project's coding style (run `black` and `isort`).
5. Write clear, descriptive commit messages.
6. Create a pull request to the `main` branch.
7. Include a description of your changes in the PR.

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/cloudflare-ufw-sync.git
cd cloudflare-ufw-sync

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=cloudflare_ufw_sync
```

## Code Style

We use the following tools to maintain code quality:

- **black**: For code formatting
- **isort**: For import sorting
- **flake8**: For code linting
- **mypy**: For type checking

To run all checks:

```bash
black src tests
isort src tests
flake8 src tests
mypy src
```

## Documentation

Good documentation is as important as good code. When contributing:

- Update README.md if needed
- Add or update docstrings for functions, classes, and modules
- Comment complex code sections

## Versioning

We follow [Semantic Versioning](https://semver.org/). When contributing, consider if your change is:

- A **patch** version (bug fix)
- A **minor** version (backward-compatible feature)
- A **major** version (breaking change)

## Commit Message Guidelines

We use conventional commits to automate versioning and changelog generation:

- `fix:` for bug fixes
- `feat:` for new features
- `docs:` for documentation changes
- `test:` for adding or updating tests
- `chore:` for maintenance tasks
- `refactor:` for code refactoring

Example: `feat: add support for IPv6 addresses`

## Thank You!

Your contributions to open source, large or small, make projects like this possible. Thank you for taking the time to contribute.