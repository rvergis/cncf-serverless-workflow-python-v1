from setuptools import setup, find_packages

setup(
    name="cncf-serverless-workflow",
    version="0.1.1",
    packages=["cncf_serverless_workflow"],
    install_requires=["pyyaml", "jq", "jsonschema", "pytest"],
    include_package_data=True,
    package_data={
        "cncf_serverless_workflow": ["workflow_schema.yaml", "workflow_example.yaml", "test_workflow_validator.py"]
    },
    author="Ron Vergis",
    description="CNCF Serverless Workflow v1.0 validator and executor",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/rvergis/cncf-serverless-workflow-python-v1",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License", "Operating System :: OS Independent"],
)