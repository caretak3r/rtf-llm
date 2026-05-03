# Lab-Only Capability Modules

These modules are for isolated, authorized lab/sandbox testing only.

## Modules

- `payload-loader`
- `persistence`
- `c2-communication`
- `data-exfiltration`
- `polymorphic-encoding`

## Run

```bash
uv run python main.py --module payload-loader
uv run python main.py --module persistence
uv run python main.py --module c2-communication
uv run python main.py --module data-exfiltration
uv run python main.py --module polymorphic-encoding
```

Enable and tune these in `config.json` before execution.
