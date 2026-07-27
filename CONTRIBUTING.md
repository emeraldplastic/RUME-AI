# Contributing to RUME AI

Thank you for your interest in contributing to RUME AI! This guide will help you get started.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/emeraldplastic/rume-ai.git
   cd rume-ai
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the development server**
   ```bash
   python run.py
   ```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Add docstrings to all public functions and classes
- Keep functions focused and under 50 lines when practical
- Use logging instead of print statements

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Write tests for any new functionality
3. Ensure all tests pass before submitting
4. Update documentation if you change public APIs
5. Submit a pull request with a clear description of your changes

## Reporting Issues

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages or logs

## Security

If you discover a security vulnerability, please report it responsibly by emailing the maintainers rather than opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
