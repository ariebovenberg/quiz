.PHONY: docs test build publish clean

init:
	poetry install

test:
	tox --parallel auto

coverage:
	pytest --cov --cov-report html --cov-report term --live

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

docs:
	@touch docs/api.rst
	make -C docs/ html

format:
	black src tests
	isort src tests
