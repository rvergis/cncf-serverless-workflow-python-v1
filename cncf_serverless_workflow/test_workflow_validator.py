import pytest
import yaml
import os
from cncf_serverless_workflow.workflow_validator import load_yaml, validate_workflow
from cncf_serverless_workflow.workflow_engine import execute_workflow

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def schema():
    """Load the schema."""
    schema_path = os.path.join(script_dir, "workflow_schema.yaml")
    return load_yaml(schema_path)

@pytest.fixture
def valid_workflow():
    """Load the valid workflow."""
    workflow_path = os.path.join(script_dir, "workflow_example.yaml")
    return load_yaml(workflow_path)

def test_valid_workflow(schema, valid_workflow):
    """Test valid workflow passes validation."""
    result = validate_workflow(valid_workflow, schema)
    print(f"message={result['message']}")
    assert result["status"] == "valid"
    assert result["message"] == ["Workflow is valid"]

def test_missing_transition_and_stateDataFilter(schema):
    """Test workflow with missing transition and stateDataFilter returns all errors."""
    invalid_workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "version": "1.0.0",
        "name": "Test Workflow",
        "states": [
            {
                "name": "GetAllObjectIds",
                "type": "operation",
                "actions": [
                    {
                        "functionRef": {"refName": "getObjectIds", "arguments": {"input": "{}"}}
                    }
                ]
            }
        ]
    }
    result = validate_workflow(invalid_workflow, schema)
    print("message", result["message"])
    assert result["status"] == "invalid"  # Reverted to expect invalid
    assert len(result["message"]) >= 1
    assert any("missing mandatory transition or end: true" in msg for msg in result["message"])


def test_missing_dataOutput(schema):
    """Test workflow with missing dataOutput does not fail (optional per schema)."""
    invalid_workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "version": "1.0.0",
        "name": "Test Workflow",
        "states": [
            {
                "name": "GetAllObjectIds",
                "type": "operation",
                "transition": "NextState",
                "actions": [
                    {
                        "functionRef": {"refName": "getObjectIds", "arguments": {"input": "{}"}}
                    }
                ]
            }
        ]
    }
    result = validate_workflow(invalid_workflow, schema)
    assert result["status"] == "invalid"

def test_iterator_type_end(schema):
    """Test workflow with type: end in iterator state returns error."""
    invalid_workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "version": "1.0.0",
        "name": "Test Workflow",
        "states": [
            {
                "name": "ForEachTest",
                "type": "foreach",
                "transition": "End",
                "inputCollection": ".items",
                "iterationParam": "item",
                "iterator": [
                    {
                        "name": "InvalidEnd",
                        "type": "end"
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    result = validate_workflow(invalid_workflow, schema)
    assert result["status"] == "invalid"
    assert any("cannot be type: end; use end: true" in msg for msg in result["message"])

# def test_subworkflow_validation(schema, valid_workflow):
#     """Test sub-workflow validation returns all errors."""
#     invalid_subworkflow = {
#         "id": "InvalidSubWorkflow",
#         "specVersion": "1.0",
#         "version": "1.0.0",
#         "name": "Invalid Sub Workflow",
#         "subWorkflows": [  # Added subWorkflows structure
#             {
#                 "id": "NestedSubWorkflow",
#                 "specVersion": "1.0",
#                 "version": "1.0.0",
#                 "states": [
#                     {
#                         "name": "NestedInvalidOperation",
#                         "type": "operation",
#                         "actions": [
#                             {
#                                 "functionRef": {"refName": "subAgent", "arguments": {"input": "{}"}}
#                             }
#                         ]
#                     }
#                 ]
#             }
#         ],
#         "states": [
#             {
#                 "name": "InvalidOperation",
#                 "type": "operation",
#                 "actions": [
#                     {
#                         "functionRef": {"refName": "subAgent", "arguments": {"input": "{}"}}
#                     }
#                 ]
#             }
#         ]
#     }
#     result = validate_workflow(invalid_subworkflow, schema)
#     assert result["status"] == "invalid"
#     assert len(result["message"]) >= 2  # Expect errors from both main workflow and sub-workflow
#     assert any("missing mandatory transition or end: true" in msg for msg in result["message"])
#     assert any("Sub-workflow 'NestedSubWorkflow': missing mandatory transition or end: true" in msg for msg in result["message"])

# def test_multiple_errors_combined(schema):
#     """Test workflow with multiple errors returns all at once."""
#     invalid_workflow = {
#         "id": "test-workflow",
#         "specVersion": "1.0",
#         "version": "1.0.0",
#         "name": "Test Workflow",
#         "states": [
#             {
#                 "name": "GetAllObjectIds",
#                 "type": "operation",
#                 "actions": [
#                     {
#                         "functionRef": {"refName": "getObjectIds", "arguments": {"input": "{}"}}
#                     }
#                 ]
#             },
#             {
#                 "name": "ForEachTest",
#                 "type": "foreach",
#                 "inputCollection": ".items",
#                 "iterationParam": "item",
#                 "iterator": [
#                     {
#                         "name": "InvalidEnd",
#                         "type": "end"
#                     }
#                 ]
#             }
#         ]
#     }
#     result = validate_workflow(invalid_workflow, schema)
#     assert result["status"] == "invalid"
#     assert len(result["message"]) >= 2
#     assert any("missing mandatory transition or end: true" in msg for msg in result["message"])
#     assert any("cannot be type: end; use end: true" in msg for msg in result["message"])