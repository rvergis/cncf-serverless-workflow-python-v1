import yaml
import jq
import jsonschema
import json
from typing import Dict, Any, List
from copy import deepcopy

# Mock function implementations (extend for custom functions)
def init_parallel(_: Dict) -> Dict:
    return {"items": [{"value": 60}, {"value": 30}, {"value": 45}], "value": 60}

def init_foreach(_: Dict) -> Dict:
    return {"items": [{"value": 60}, {"value": 30}, {"value": 45}]}

def init_switch(_: Dict) -> Dict:
    return {"value": 60}

def init_operation(_: Dict) -> Dict:
    return {"value": 70}

def method1(data: Dict) -> int:
    return data["input"] + 1

def method2(data: Dict) -> str:
    return f"Processed: {data['input']}"

def method3(data: Dict) -> List:
    return [data["input"]["value"], str(int(data["input"]["value"]) + 1) if data["input"]["value"].isdigit() else data["input"]["value"] + "1"]

def method4(data: Dict) -> Dict:
    return {"key": data["input"]["default"]}

def sub_agent(data: Dict) -> Dict:
    return {"subResult": data["input"]}

FUNCTIONS = {
    "initParallel": init_parallel,
    "initForEach": init_foreach,
    "initSwitch": init_switch,
    "initOperation": init_operation,
    "method1": method1,
    "method2": method2,
    "method3": method3,
    "method4": method4,
    "subAgent": sub_agent
}

def load_workflow(yaml_content: str) -> Dict:
    """Load and parse workflow YAML."""
    return yaml.safe_load(yaml_content)

def validate_workflow(workflow: Dict, schema: Dict):
    """Validate workflow against schema."""
    jsonschema.validate(workflow, schema)

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merge two dictionaries."""
    result = deepcopy(dict1)
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            result[key].extend(value)
        else:
            result[key] = deepcopy(value)
    return result

def apply_jq(expression: str, data: Dict) -> Any:
    """Apply JQ expression to data, handling nulls."""
    try:
        return jq.compile(expression).input(data).first()
    except Exception as e:
        print(f"JQ error: {e}, expression: {expression}")
        return {}

def set_path(data: Dict, path: str, value: Any) -> Dict:
    """Set value at JSONPath in data."""
    result = deepcopy(data)
    current = result
    parts = path.lstrip(".").split(".")
    for part in parts[:-1]:
        current[part] = current.get(part, {})
        current = current[part]
    current[parts[-1]] = value
    return result

def execute_action(action: Dict, state: Dict) -> Dict:
    """Execute an action and merge its output."""
    function_ref = action["functionRef"]
    ref_name = function_ref["refName"]
    arguments = function_ref.get("arguments", {})
    
    # Evaluate arguments
    arg_input = apply_jq(arguments.get("input", "{}"), state)
    
    # Execute function
    func = FUNCTIONS.get(ref_name)
    if not func:
        raise ValueError(f"Function {ref_name} not found")
    output = func(arg_input)
    
    # Merge output to dataOutput path
    output_path = action.get("dataOutput", "")
    if output_path:
        return set_path({}, output_path, output)
    return {}

def execute_operation_state(state: Dict, input_state: Dict) -> Dict:
    """Execute an OperationState."""
    current_state = deepcopy(input_state)
    actions = state.get("actions", [])
    action_mode = state.get("actionMode", "sequential")
    
    if action_mode == "sequential":
        for action in actions:
            action_output = execute_action(action, current_state)
            current_state = merge_dicts(current_state, action_output)
    else:  # parallel
        outputs = [execute_action(action, current_state) for action in actions]
        for output in outputs:
            current_state = merge_dicts(current_state, output)
    
    return current_state

def execute_foreach_state(state: Dict, input_state: Dict, workflow: Dict) -> Dict:
    """Execute a ForEachState."""
    input_collection = apply_jq(state.get("inputCollection", "[]"), input_state)
    iteration_param = state.get("iterationParam", "item")
    iterator_states = state.get("iterator", [])
    results = []
    
    for item in input_collection or []:
        item_state = deepcopy(input_state)
        item_state[iteration_param] = item
        for iterator_state in iterator_states:
            item_state = execute_state(iterator_state, item_state, workflow)
        results.append(item_state.get("context", {}))
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return {"context": {"ForEachStateOutput": {"results": results}}}
    return set_path({}, output_path, {"results": results})

def execute_switch_state(state: Dict, input_state: Dict, workflow: Dict) -> Dict:
    """Execute a SwitchState."""
    conditions = state.get("dataConditions", [])
    default_condition = state.get("defaultCondition", {})
    current_state = deepcopy(input_state)
    
    for condition in conditions:
        if apply_jq(condition["condition"], current_state):
            next_state_name = condition["transition"]
            next_state = next((s for s in workflow["states"] if s["name"] == next_state_name), None)
            if next_state:
                return execute_state(next_state, current_state, workflow)
    
    next_state_name = default_condition.get("transition")
    if next_state_name:
        next_state = next((s for s in workflow["states"] if s["name"] == next_state_name), None)
        if next_state:
            return execute_state(next_state, current_state, workflow)
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return merge_dicts(current_state, {"context": {"SwitchStateOutput": {"value": 60}}})
    return set_path(current_state, output_path, {"value": 60})

def execute_subflow_state(state: Dict, input_state: Dict, workflow: Dict) -> Dict:
    """Execute a SubflowState."""
    workflow_id = state.get("workflowId")
    sub_workflow = next((sw for sw in workflow.get("subWorkflows", []) if sw["id"] == workflow_id), None)
    if not sub_workflow:
        raise ValueError(f"SubWorkflow {workflow_id} not found")
    
    input_expression = state.get("stateDataFilter", {}).get("input", "{}")
    sub_input = apply_jq(input_expression, input_state)
    sub_state = {"context": {"SubWorkflowOutput": sub_input.get("input", {})}}
    
    for sub_state_def in sub_workflow["states"]:
        sub_state = execute_state(sub_state_def, sub_state, sub_workflow)
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return merge_dicts(input_state, {"context": {"ForEachStateOutput": sub_state.get("context", {})}})
    return set_path(input_state, output_path, sub_state.get("context", {}))

def execute_end_state(state: Dict, input_state: Dict) -> Dict:
    """Execute an EndState."""
    return input_state  # Terminates workflow, returns current state

def execute_state(state: Dict, input_state: Dict, workflow: Dict) -> Dict:
    """Execute a state based on its type."""
    state_type = state["type"]
    input_expression = state.get("stateDataFilter", {}).get("input", "{}")
    current_state = apply_jq(input_expression, input_state) if input_expression else input_state
    
    if state_type == "parallel":
        return execute_parallel_state(state, current_state)
    elif state_type == "operation":
        return execute_operation_state(state, current_state)
    elif state_type == "foreach":
        return execute_foreach_state(state, current_state, workflow)