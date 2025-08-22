.PHONY: install test build patch publish force-publish clean

install:
	pip install --upgrade pip
	pip install setuptools wheel twine pytest

test:
	pytest cncf_serverless_workflow/test_workflow_validator.py cncf_serverless_workflow/test_workflow_engine.py

build:
	python setup.py sdist bdist_wheel

# Bump the patch version in cncf_serverless_workflow/__init__.py and setup.py
patch:
	@echo "Reading and bumping version from cncf_serverless_workflow/__init__.py..."
	@if [ ! -f cncf_serverless_workflow/__init__.py ]; then echo "Error: cncf_serverless_workflow/__init__.py not found"; exit 1; fi
	@if [ ! -f setup.py ]; then echo "Error: setup.py not found"; exit 1; fi
	$(eval OLD_VERSION := $(shell grep "__version__" cncf_serverless_workflow/__init__.py | cut -d'"' -f2))
	$(eval PARTS := $(subst ., ,$(OLD_VERSION)))
	$(eval MAJOR := $(word 1,$(PARTS)))
	$(eval MINOR := $(word 2,$(PARTS)))
	$(eval PATCH := $(word 3,$(PARTS)))
	$(eval NEW_VERSION := $(MAJOR).$(MINOR).$(shell expr $(PATCH) + 1))
	@echo "Bumping version from $(OLD_VERSION) to $(NEW_VERSION)"
	@sed -i.bak "s/__version__ = \"$(OLD_VERSION)\"/__version__ = \"$(NEW_VERSION)\"/g" cncf_serverless_workflow/__init__.py && rm -f cncf_serverless_workflow/__init__.py.bak
	@sed -i.bak "s/version=\"$(OLD_VERSION)\"/version=\"$(NEW_VERSION)\"/g" setup.py && rm -f setup.py.bak
	@git add cncf_serverless_workflow/__init__.py setup.py
	@git commit -m "Bump version to $(NEW_VERSION)" || echo "No changes to commit or Git not initialized"
	@echo "Version bumped to $(NEW_VERSION) and committed"

# Publish the package by tagging the version and pushing to GitHub
publish:
	@echo "Reading version from cncf_serverless_workflow/__init__.py..."
	@if [ ! -f cncf_serverless_workflow/__init__.py ]; then echo "Error: cncf_serverless_workflow/__init__.py not found"; exit 1; fi
	$(eval VERSION := $(shell grep "__version__" cncf_serverless_workflow/__init__.py | cut -d'"' -f2))
	@if [ -z "$(VERSION)" ]; then echo "Error: Could not extract version from cncf_serverless_workflow/__init__.py"; exit 1; fi
	@if git rev-parse "v$(VERSION)" >/dev/null 2>&1; then echo "Error: Tag v$(VERSION) already exists"; exit 1; fi
	@echo "Creating tag v$(VERSION)"
	@git tag v$(VERSION)
	@echo "Pushing tag v$(VERSION) to origin"
	@git push origin v$(VERSION) || echo "Error: Failed to push tag v$(VERSION), ensure remote is configured"
	@echo "Triggered GitHub Actions workflow for publishing v$(VERSION)"

force-publish:
	@echo "Force-publishing version..."
	$(eval VERSION := $(shell grep "__version__" __init__.py | cut -d'"' -f2))
	@git tag -f v$(VERSION)
	@git push origin v$(VERSION) --force
	@echo "Triggered GitHub Actions workflow for publishing $(VERSION)"

clean:
	rm -rf dist build *.egg-info