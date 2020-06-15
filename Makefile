SHELL=/bin/sh
VENV=.venv

.PHONY: all build dev lint test clean distclean

all: build

${VENV}:
	python3 -m venv ${VENV}
	${VENV}/bin/pip install --upgrade pip setuptools wheel

build: ${VENV}
	source ${VENV}/bin/activate; python setup.py sdist bdist_wheel

dev: ${VENV}
	source ${VENV}/bin/activate; pip install -e .[test]

lint: dev
	${VENV}/bin/flake8 --max-line-length=120 gifts tests

test: dev
	${VENV}/bin/pytest --cov=gifts tests

clean: distclean
	rm -rf ${VENV}
	find . -name '*.py[co~]' -exec rm -f {} +
	find . -type d -name '__pycache__' -exec rm -rf {} +

distclean:
	find . -name '*.egg-info' -exec rm -rf {} +
	rm -rf .cache .eggs .pytest_cache build dist
