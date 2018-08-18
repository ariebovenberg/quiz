.PHONY: docs test build publish clean

init:
	pip install -r requirements/dev.txt

test:
	detox

test-examples:
	pytest examples/

coverage:
	pytest --cov=quiz --cov-report html --cov-report term --cov-fail-under 100

publish: clean
	rm -rf build dist .egg quiz.egg-info
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf
	python setup.py clean --all

docs:
	@touch docs/api.rst
	make -C docs/ html
