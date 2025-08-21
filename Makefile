.PHONY: install test build patch publish clean

install:
	pip install --upgrade pip
	pip install setuptools wheel twine pytest

test:
	pytest test-workflow-validator.py

build:
	python setup.py sdist bdist_wheel

patch:
	@echo "Reading and bumping version from __init__.py..."
	$(eval OLD_VERSION := $(shell grep "__version__" __init__.py | cut -d'"' -f2))
	$(eval PARTS := $(subst ., ,$(OLD_VERSION)))
	$(eval MAJOR := $(word 1,$(PARTS)))
	$(eval MINOR := $(word 2,$(PARTS)))
	$(eval PATCH := $(word 3,$(PARTS)))
	$(eval NEW_VERSION := $(MAJOR).$(MINOR).$(shell expr $(PATCH) + 1))
	@sed -i '' "s/__version__ = \"$(OLD_VERSION)\"/__version__ = \"$(NEW_VERSION)\"/g" __init__.py
	@echo "Bumped version to $(NEW_VERSION)"
	@git add __init__.py
	@git commit -m "Bump version to $(NEW_VERSION)"

publish:
	@echo "Publishing version..."
	$(eval VERSION := $(shell grep "__version__" __init__.py | cut -d'"' -f2))
	@git tag v$(VERSION)
	@git push origin v$(VERSION)
	@echo "Triggered GitHub Actions workflow for publishing $(VERSION)"

clean:
	rm -rf dist build *.egg-info