# Commands
test: PYTHONPATH=. python -m pytest tests/ --cov=wol_app --cov-report=term-missing --html=tests/reports/report.html --self-contained-html -v
build: flet build apk --build-version 0.7.3 --build-number 1 --org com.intelout.wol
typecheck: mypy main.py wol_app/
lint: ruff check . && pylint main.py wol_app/ tests/
all: ruff check . && mypy main.py wol_app/ && pylint main.py wol_app/ tests/ && PYTHONPATH=. python -m pytest tests/ --cov=wol_app --cov-report=term-missing --html=tests/reports/report.html --self-contained-html -v
