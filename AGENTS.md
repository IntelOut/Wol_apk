# Commands
test: PYTHONPATH=. python -m pytest tests/ --cov=wol_app --cov-report=term-missing -v
build: flet build apk --icon assets/icon.png --build-version 0.5.2 --build-number 1 --org com.intelout.wol --orientation portrait
