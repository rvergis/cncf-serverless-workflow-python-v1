import pytest
import yaml
from validate_workflow import load_yaml, validate_workflow

@pytest.fixture
def schema():
    """Load the schema."""
    return load_yaml("workflow-schema.yaml")

@pytest.fixture
def valid_workflow():
    """Load the valid workflow."""
    return load_yaml("simplified-agentic-workflow.yaml")

def test_valid_workflow(schema, valid_workflow):
    """Test valid workflow passes validation."""
    result = validate_workflow(valid_workflow, schema)
    assert result["status"] == "valid"
    assert result["message"] == "Workflow is valid"

def test_missing_transition(schema):
    """Test workflow with missing transition fails."""
    invalid_workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "version": "1.0.0",
        "name": "Test Workflow",
        "states": [
            {
                "name": "GetAllObjectIds",
                "type": "operation",
                "stateDataFilter": {"input": "{}", "output": ".context"},
                "actions": [
                    {
                        "functionRef": {"refName": "getObjectIds", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.GetAllObjectIdsOutput.objectIds"
                    }
                ]
            }
        ]
    }
    result = validate_workflow(invalid_workflow, schema)
    assert result["status"] == "invalid"
    assert "missing mandatory transition or end: true" in result["message"]

def test_missing_stateDataFilter(schema):
    """Test workflow with missing stateDataFilter fails."""
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
                        "functionRef": {"refName": "getObjectIds", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.GetAllObjectIdsOutput.objectIds"
                    }
                ]
            }
        ]
    }
    result = validate_workflow(invalid_workflow, schema)
    assert result["status"] == "invalid"
    assert "missing mandatory stateDataFilter" in result["message"]

def test_missing_dataOutput(schema):
    """Test workflow with missing dataOutput fails."""
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
                "stateDataFilter": {"input": "{}", "output": ".context"},
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
    assert "missing mandatory dataOutput" in result["message"]

def test_iterator_type_end(schema):
    """Test workflow with type: end in iterator state fails."""
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
                "stateDataFilter": {"input": "{}", "output": ".context"},
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
    assert "cannot be type: end; use end: true" in result["message"]

def test_subworkflow_validation(schema, valid_workflow):
    """Test sub-workflow validation."""
    sub_workflow = valid_workflow["subWorkflows"][0]
    result = validate_workflow(sub_workflow, schema)
    assert result["status"] == "valid"
    assert result["message"] == "Workflow is valid"