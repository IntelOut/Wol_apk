# Commands
test: PYTHONPATH=. python -m pytest tests/ --cov=wol_app --cov-report=term-missing -v
build: flet build apk --build-version 0.6.0 --build-number 1 --org com.intelout.wol
