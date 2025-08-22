"""CNCF Serverless Workflow v1.0 Python package.

Provides validation and execution for CNCF Serverless Workflow v1.0 specifications.
"""

from .workflow_validator import load_yaml, validate_workflow
from .workflow_engine import execute_workflow, validate_state_flow

__version__ = "0.1.0"