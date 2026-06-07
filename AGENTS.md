# Commands
test: python -m pytest tests/ --cov=main --cov-report=term-missing -v
build: flet build apk --icon assets/icon.png --build-version 0.5.0 --build-number 1 --org com.intelout.wol --orientation portrait
