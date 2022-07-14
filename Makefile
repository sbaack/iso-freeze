.PHONY: help update-dev-deps setup clean pipx-upload pipx-publish upload publish test

help:
	@echo 'clean:           remove dist and .egg-info directory'
	@echo 'pipx-publish:    publish new version on pypi.org using pipx run'
	@echo 'publish:         publish new version on pypi.org using local installs'
	@echo 'test:            run all tests'
	@echo 'update-dev-deps: update pip and dev dependencies'
	@echo 'setup:           editiable install of archive-md-urls'

update-dev-deps:
	python -m pip install -U pip
	python -m pip install -Ue .[dev]

setup: update-dev-deps

clean:
	rm -rf dist
	rm -rf src/*.egg-info

pipx-upload: clean
	pipx run build
	pipx run twine check dist/*
	pipx run twine upload dist/*

pipx-publish: upload clean

upload: clean
	python -m pip install -U build twine
	build
	twine check dist/*
	twine upload dist/*

publish: upload clean

test:
	python -m pytest
