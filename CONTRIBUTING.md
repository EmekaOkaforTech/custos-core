# Contributing

Thanks for helping improve Custos Core.

## Principles
- Local-first by default (no outbound calls without explicit opt-in).
- Deterministic behavior over probabilistic output.
- Source-first and auditable data paths.
- Minimal operational complexity.

## Development setup
```bash
export CUSTOS_DATABASE_KEY="your-key"
make dev
```

## Tests
```bash
pytest -q
node custos-core/frontend/tests/ui-state.test.mjs
```

## Code style
- Python: 4 spaces, clear names, avoid side effects.
- Frontend: plain JS/HTML/CSS with calm UI patterns.
- Prefer small, explicit changes over large refactors.

## Pull requests
- Keep scope tight.
- Include test updates where behavior changes.
- Avoid adding new dependencies unless required for core trust or security.
