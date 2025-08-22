import pytest
import yaml
import os
from cncf_serverless_workflow.workflow_engine import execute_workflow, validate_state_flow
from cncf_serverless_workflow.workflow_validator import load_yaml
from typing import Dict, List, Callable

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def schema():
    """Load the workflow schema."""
    schema_path = os.path.join(script_dir, "workflow_schema.yaml")
    return load_yaml(schema_path)

@pytest.fixture
def init_parallel():
    """Fixture for initParallel function."""
    def _init_parallel(_: Dict) -> Dict:
        return {"items": [{"value": 60}, {"value": 30}, {"value": 45}], "value": 60}
    return _init_parallel

@pytest.fixture
def produce_data():
    """Fixture for produceData function."""
    def _produce_data(_: Dict) -> List:
        return [{"value": 1}, {"value": 2}, {"value": 3}]
    return _produce_data

@pytest.fixture
def process_item():
    """Fixture for processItem function."""
    def _process_item(data: Dict) -> Dict:
        return {"result": data.get("value", 0)}
    return _process_item

@pytest.fixture
def method1():
    """Fixture for method1 function."""
    def _method1(data: int) -> int:
        return data + 1
    return _method1

@pytest.fixture
def method2():
    """Fixture for method2 function."""
    def _method2(data: str) -> str:
        return f"Processed: {data}"
    return _method2

def test_execute_valid_workflow(init_parallel):
    """Test execution of a valid workflow with data output."""
    workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "start": "Start",
        "states": [
            {
                "name": "Start",
                "type": "operation",
                "transition": "End",
                "actions": [
                    {
                        "functionRef": {"refName": "initParallel", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.startOutput"
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"initParallel": init_parallel}
    result = execute_workflow(workflow, functions=functions)
    assert "context" in result
    assert "startOutput" in result["context"]
    assert result["context"]["startOutput"]["items"] == [{"value": 60}, {"value": 30}, {"value": 45}]
    assert result["context"]["startOutput"]["value"] == 60

def test_execute_missing_dataOutput(init_parallel):
    """Test execution fails gracefully with missing dataOutput."""
    workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "start": "Start",
        "states": [
            {
                "name": "Start",
                "type": "operation",
                "transition": "End",
                "actions": [
                    {
                        "functionRef": {"refName": "initParallel", "arguments": {"input": "{}"}}
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"initParallel": init_parallel}
    result = execute_workflow(workflow, functions=functions)
    assert "context" in result
    assert "startOutput" not in result["context"]

def test_validate_state_flow_valid(produce_data, process_item):
    """Test validate_state_flow with a valid data flow."""
    workflow = {
        "id": "test-flow",
        "specVersion": "1.0",
        "start": "ProduceData",
        "states": [
            {
                "name": "ProduceData",
                "type": "operation",
                "transition": "ConsumeData",
                "actions": [
                    {
                        "functionRef": {"refName": "produceData", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.producedData"
                    }
                ]
            },
            {
                "name": "ConsumeData",
                "type": "foreach",
                "transition": "End",
                "inputCollection": ".context.producedData",
                "iterationParam": "item",
                "iterator": [
                    {
                        "name": "ProcessItem",
                        "type": "operation",
                        "actions": [
                            {
                                "functionRef": {"refName": "processItem", "arguments": {"input": ".item"}},
                                "dataOutput": ".context.processedItem"
                            }
                        ],
                        "end": True
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"produceData": produce_data, "processItem": process_item}
    result = validate_state_flow(workflow, functions=functions)
    assert result["message"] == ["Data flow is consistent"], result["message"]
    assert result["status"] == "valid"

def test_validate_state_flow_invalid(produce_data, process_item):
    """Test validate_state_flow with an invalid data flow."""
    workflow = {
        "id": "test-flow",
        "specVersion": "1.0",
        "start": "ProduceData",
        "states": [
            {
                "name": "ProduceData",
                "type": "operation",
                "transition": "ConsumeData",
                "actions": [
                    {
                        "functionRef": {"refName": "produceData", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.producedData"
                    }
                ]
            },
            {
                "name": "ConsumeData",
                "type": "foreach",
                "transition": "End",
                "inputCollection": ".context.unrelatedData",
                "iterationParam": "item",
                "iterator": [
                    {
                        "name": "ProcessItem",
                        "type": "operation",
                        "actions": [
                            {
                                "functionRef": {"refName": "processItem", "arguments": {"input": ".item"}},
                                "dataOutput": ".context.processedItem"
                            }
                        ],
                        "end": True
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"produceData": produce_data, "processItem": process_item}
    result = validate_state_flow(workflow, functions=functions)
    assert result["status"] == "invalid"
    assert len(result["message"]) >= 1
    assert any("inputCollection '.context.unrelatedData' references undefined or empty data" in msg for msg in result["message"])

def test_execute_parallel_state(method1, method2):
    """Test execution of a parallel state with multiple branches."""
    workflow = {
        "id": "test-workflow",
        "specVersion": "1.0",
        "start": "ParallelStart",
        "states": [
            {
                "name": "ParallelStart",
                "type": "parallel",
                "transition": "End",
                "branches": [
                    {
                        "name": "Branch1",
                        "states": [
                            {
                                "name": "Branch1Op",
                                "type": "operation",
                                "actions": [
                                    {
                                        "functionRef": {"refName": "method1", "arguments": {"input": 5}},
                                        "dataOutput": ".context.branch1"
                                    }
                                ],
                                "end": True
                            }
                        ]
                    },
                    {
                        "name": "Branch2",
                        "states": [
                            {
                                "name": "Branch2Op",
                                "type": "operation",
                                "actions": [
                                    {
                                        "functionRef": {"refName": "method2", "arguments": {"input": "test"}},
                                        "dataOutput": ".context.branch2"
                                    }
                                ],
                                "end": True
                            }
                        ]
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"method1": method1, "method2": method2}
    result = execute_workflow(workflow, functions=functions)
    assert "context" in result
    assert "branch1" in result["context"]
    assert result["context"]["branch1"] == 6
    assert "branch2" in result["context"]
    assert result["context"]["branch2"] == "Processed: test"

def test_validate_state_flow_intermediate_results(produce_data, process_item):
    """Test validate_state_flow captures correct intermediate state inputs and outputs."""
    workflow = {
        "id": "test-flow",
        "specVersion": "1.0",
        "start": "ProduceData",
        "states": [
            {
                "name": "ProduceData",
                "type": "operation",
                "transition": "ConsumeData",
                "actions": [
                    {
                        "functionRef": {"refName": "produceData", "arguments": {"input": "{}"}},
                        "dataOutput": ".context.producedData"
                    }
                ]
            },
            {
                "name": "ConsumeData",
                "type": "foreach",
                "transition": "End",
                "inputCollection": ".context.producedData",
                "iterationParam": "item",
                "iterator": [
                    {
                        "name": "ProcessItem",
                        "type": "operation",
                        "actions": [
                            {
                                "functionRef": {"refName": "processItem", "arguments": {"input": ".item"}},
                                "dataOutput": ".context.processedItem"
                            }
                        ],
                        "end": True
                    }
                ]
            },
            {
                "name": "End",
                "type": "end"
            }
        ]
    }
    functions = {"produceData": produce_data, "processItem": process_item}
    result = validate_state_flow(workflow, functions=functions)
    assert result["status"] == "valid"
    assert result["message"] == ["Data flow is consistent"], result["message"]
    
    # Verify intermediate results
    intermediate_results = result["intermediate_results"]
    assert len(intermediate_results) == 4  # ProduceData + 3 iterations of ProcessItem
    
    # Check ProduceData state
    produce_data_result = next(r for r in intermediate_results if r["state"] == "ProduceData")
    assert produce_data_result["input"] == {"context": {}}
    assert produce_data_result["output"] == {
        "context": {
            "producedData": [{"value": 1}, {"value": 2}, {"value": 3}]
        }
    }
    
    # Check ProcessItem state (3 iterations)
    process_item_results = [r for r in intermediate_results if r["state"] == "ProcessItem"]
    assert len(process_item_results) == 3
    expected_values = [1, 2, 3]
    for i, res in enumerate(process_item_results):
        assert res["input"]["item"] == {"value": expected_values[i]}
        assert res["input"]["context"] == {"producedData": [{"value": 1}, {"value": 2}, {"value": 3}]}
        assert res["output"]["item"] == {"value": expected_values[i]}
        assert res["output"]["context"] == {
            "producedData": [{"value": 1}, {"value": 2}, {"value": 3}],
            "processedItem": {"result": expected_values[i]}
        }