# Commands
test: python -m pytest test_main.py --cov=main --cov-report=term-missing -v
build: flet build apk --icon icon.png --build-version 0.3.0 --build-number 1 --org com.intelout.wol --orientation portrait
