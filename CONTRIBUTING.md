# Contributing to Enterprise Agent Orchestrator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/enterprise-agent-orchestrator.git
   cd enterprise-agent-orchestrator
   ```

3. Set up development environment:
   ```bash
   make dev-setup
   ```

4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Before You Code

- Check existing issues and pull requests to avoid duplicates
- For major changes, open an issue first to discuss your approach
- Review the [Architecture Decision Records](docs/adr/) to understand design principles

### Writing Code

**Code Standards:**

- Use Python 3.12+ features
- Add type hints to all functions
- Follow PEP 8 style guide (enforced by Ruff)
- Write docstrings for all public APIs
- Keep functions focused and testable

**Example:**

```python
async def calculate_risk_score(
    agent_metadata: dict[str, Any]
) -> RiskScore:
    """
    Calculate risk score for an agent.

    Args:
        agent_metadata: Dictionary with agent configuration and history.

    Returns:
        RiskScore with total score and recommendations.
    """
    # Implementation
```

### Testing

All code changes must include tests:

```bash
# Run tests
make test

# Run specific test file
pytest tests/test_governance/test_risk_scorer.py

# Run with coverage
pytest --cov
```

**Coverage Requirements:**
- Overall: 90%+
- New code: 95%+

### Code Quality

Run quality checks before committing:

```bash
# Lint check
make lint

# Auto-format
make format

# Type check
make typecheck

# All checks
make lint && make typecheck && make test
```

Pre-commit hooks run automatically on commit.

### Commit Messages

Use clear, descriptive commit messages:

```
Add PII detection for credit card numbers

- Implement Luhn algorithm validation
- Add confidence scoring
- Include tests for valid/invalid cards
- Update documentation

Closes #123
```

Format:
- First line: Brief summary (50 chars max)
- Blank line
- Detailed description (wrap at 72 chars)
- Reference related issues

### Pull Request Process

1. **Update Documentation:**
   - Add/update docstrings
   - Update README if needed
   - Add ADR for architectural changes

2. **Create Pull Request:**
   - Use descriptive title
   - Fill out PR template
   - Link related issues
   - Add screenshots for UI changes

3. **Code Review:**
   - Address reviewer feedback
   - Keep discussion professional
   - Update based on suggestions

4. **Merge:**
   - Squash commits if requested
   - Ensure CI passes
   - Wait for maintainer approval

## Types of Contributions

### Bug Fixes

- Search existing issues first
- Include minimal reproduction case
- Add regression test
- Reference issue number in commit

### New Features

- Discuss in issue before implementation
- Follow existing patterns
- Include comprehensive tests
- Update documentation

### Documentation

- Fix typos, improve clarity
- Add examples
- Keep language simple and active
- Test code examples

### Performance Improvements

- Include benchmark results
- Explain trade-offs
- Consider backward compatibility
- Add performance tests

## Project Structure

```
enterprise-agent-orchestrator/
├── apps/               # Applications
│   ├── orchestrator/   # FastAPI app
│   ├── worker/         # Temporal worker
│   └── agent-runtime/  # Agent execution
├── packages/           # Shared libraries
│   ├── domain-models/  # Database models
│   ├── governance-sdk/ # Policy, PII, risk
│   └── mcp-adapter/    # MCP integration
├── tests/              # Test suite
├── docs/               # Documentation
└── scripts/            # Utility scripts
```

## Testing Guidelines

### Unit Tests

Test individual components in isolation:

```python
def test_risk_scorer_low_risk_agent(risk_scorer: RiskScorer) -> None:
    """Test scoring for low-risk agent."""
    metadata = {"data_access": {"classification": "public"}}
    result = risk_scorer.calculate(metadata)
    assert result.risk_level == "low"
```

### Integration Tests

Test components working together:

```python
@pytest.mark.asyncio
async def test_agent_approval_workflow(
    client: AsyncClient,
    admin_token: str,
    sample_agent: Agent,
) -> None:
    """Test complete approval workflow."""
    # Submit for approval
    # Approve as admin
    # Verify status changes
```

### Fixtures

Use pytest fixtures for reusable test data:

```python
@pytest_asyncio.fixture
async def sample_agent(session: AsyncSession) -> Agent:
    """Create test agent."""
    agent = Agent(name="Test Agent", ...)
    session.add(agent)
    await session.commit()
    return agent
```

## Documentation Standards

### Docstrings

Use Google-style docstrings:

```python
def process_data(input_data: dict[str, Any], validate: bool = True) -> Result:
    """
    Process input data and return result.

    Args:
        input_data: Raw data to process.
        validate: Whether to validate before processing.

    Returns:
        Processed result with metadata.

    Raises:
        ValueError: If validation fails and validate=True.

    Example:
        >>> result = process_data({"key": "value"})
        >>> print(result.status)
        'success'
    """
```

### README Updates

- Keep language clear and concise
- Use active voice
- Add code examples
- Include screenshots for visual changes

### ADRs

For architectural changes, create an ADR:

```markdown
# ADR XXX: Title

**Status:** Proposed / Accepted / Deprecated

**Date:** YYYY-MM-DD

## Context
[Describe the problem]

## Decision
[Describe the solution]

## Consequences
[Describe impacts]
```

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Create a GitHub Issue
- **Security:** Email security@company.com

## Recognition

Contributors are recognized in:
- Release notes
- CONTRIBUTORS.md file
- Project README

Thank you for contributing!
