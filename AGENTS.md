# AGENTS.md

## Cursor Cloud specific instructions

This is a Python desktop/CLI project (no Node, no DB, no services). It transforms flat
hardware-store catalogs (Excel/PDF) into a WooCommerce-ready master format. There are two
entry points: a CLI pipeline (`main.py`) and a Tkinter review GUI (`revisor_gui.py`).

### Environment
- Python deps live in a virtualenv at `.venv` (the update script creates/refreshes it).
  Run everything with `.venv/bin/python` (or `source .venv/bin/activate`).
- System packages `python3-venv` and `python3-tk` are pre-installed in the VM snapshot.
  `python3-tk` is required for the Tkinter GUI; it is not a pip dependency.
- A VNC desktop is available on `DISPLAY=:1`. Launch the GUI with
  `DISPLAY=:1 .venv/bin/python revisor_gui.py [optional_xlsx]`.

### Run / lint / test
- CLI pipeline (core flow): `.venv/bin/python create_example.py` then
  `printf '\n' | .venv/bin/python main.py --input data/raw/ejemplo_productos.xlsx`.
  `main.py` is interactive: it prompts for an input file when `--input` is omitted and
  always waits for a final Enter, so pipe a newline when running non-interactively.
  It writes `maestro_revision_*.xlsx/.csv` and `woocommerce_import_*.csv` into
  `data/processed/` (gitignored).
- GUI: see launch command above.
- Lint: `.venv/bin/black --check .` (black is a dev tool, not enforced; the repo is not
  currently black-formatted, so this reports many "would reformat" files — expected).
- Tests: `.venv/bin/python -m pytest test_pipeline.py tests/ -q`.

### Known pre-existing test failures (NOT environment issues — do not "fix" as setup)
- `test_pipeline.py`: 3 of 6 tests fail because the test code is out of date with the
  current module API (e.g. `generate_master_format` now returns 4 values, master format
  uses different column names). Run as a script (`.venv/bin/python test_pipeline.py`) to
  see the same 3 pass / 3 fail.
- `tests/test_spatial_parser.py`: ~20 pass, ~38 `TestCatalogStructure` errors because a
  fixture hardcodes a Windows path `c:\Users\yubyr\...\pdf\Catalogo_Mamut_2025.txt`. The
  file actually exists at `pdf/Catalogo_Mamut_2025.txt` in the repo, but the absolute path
  does not resolve on Linux. The non-structure tests pass.
