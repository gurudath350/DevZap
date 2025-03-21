# DevZap

DevZap is an AI-powered CLI tool for DevOps, offering error analysis, tool installation, and log monitoring with optional automation. Powered by OpenRouter's API.

## Setup
1. Install: `pip install -r requirements.txt`
2. Run: `python src/devzap.py setup` or set `DEVZAP_API_KEY` env var

## Usage
- Analyze error: `python src/devzap.py analyze --file error.log [--auto]`
- Install tool: `python src/devzap.py install --tool docker [--auto]`
- Monitor logs: `python src/devzap.py monitor --log-file app.log [--auto]`
- List models: `python src/devzap.py list-models`

## Automation
Use `--auto` to execute suggested commands automatically (e.g., fixes or installs). Without it, you’ll be prompted to confirm each command.

## License
MIT - see [LICENSE](LICENSE)
