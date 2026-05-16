# Character Manager

Character management service — part of the [character-vault](https://github.com/marthox/character-vault) platform.

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest

# Run locally
fastapi dev src/main.py
```

## Docker

This service is built and run via the character-vault orchestrator.

```bash
# From the character-vault root
docker-compose up --build character-manager
```
