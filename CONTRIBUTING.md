# Contributing to AMRE_MAD

Thank you for your interest in contributing! These guidelines help keep the codebase consistent and the review process smooth.

## Getting Started

1. **Fork** the repository and clone it locally
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a **feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

## Development Guidelines

### Code Style
- Follow **PEP 8** for all Python code
- Add docstrings to every public function and class (NumPy or Google style)
- Keep modules focused – `src/` is the library, `scripts/` are entry points, `tools/` for standalone utilities

### Paths — Never Hardcode
Always use the constants from `src/config.py` or derive paths dynamically:
```python
# Good
from src.config import MOTORS_DIR, DB_PATH

# Bad
motors_dir = r"C:\Users\yourname\...\motors"
```

### Adding a New Feature
1. Add or modify the relevant module in `src/`
2. Expose it through the appropriate script in `scripts/`
3. Update `docs/` if the feature adds user-visible behaviour
4. If new configuration keys are needed, add them to `src/config.py` with descriptive comments

### Adding a New Dependency
- Add it to `requirements.txt` with a minimum version pin (`package>=x.y`)
- Document why it is needed in a comment above the entry

## Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat: add batch export to CSV
fix: handle missing Lab/ folder gracefully
docs: update GUI web usage guide
refactor: extract quality-check logic into src/quality.py
```

## Pull Request Process

1. Ensure there are no remaining absolute paths and no `*.db` or `generated_pdfs/` files staged
2. Fill in the **PR template** completely
3. Request a review – PRs are merged by at least one maintainer

## Reporting Bugs

Open an issue using the **Bug report** template and include:
- Full traceback
- Motor file name (or a minimal reproducer)
- MotorCAD version and Python version
