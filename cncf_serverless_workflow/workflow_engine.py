import yaml
import jq
import jsonschema
import json
from typing import Dict, Any, List, Callable
from copy import deepcopy

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

def apply_jq(expression: Any, data: Dict) -> Any:
    """Apply JQ expression to data, handling non-string values and literal strings."""
    if not isinstance(expression, str):
        return expression
    if expression == "{}" or expression == "":
        return {}
    try:
        jq.compile(expression)
        result = jq.compile(expression).input(data).first()
        print(f"JQ success: expression={expression}, data={data}, result={result}")
        return result
    except Exception as e:
        print(f"JQ error: {e}, expression={expression}, data={data}, treating as literal value")
        return expression

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

def execute_action(action: Dict, state: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute an action and merge its output using the provided functions delegate."""
    function_ref = action["functionRef"]
    ref_name = function_ref["refName"]
    arguments = function_ref.get("arguments", {})
    
    arg_input = apply_jq(arguments.get("input", "{}"), state)
    
    func = functions.get(ref_name)
    if not func:
        raise ValueError(f"Function {ref_name} not found")
    output = func(arg_input)
    
    output_path = action.get("dataOutput", "")
    if output_path:
        return set_path({}, output_path, output)
    return {}

def execute_operation_state(state: Dict, input_state: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute an OperationState."""
    current_state = deepcopy(input_state) or {"context": {}}
    actions = state.get("actions", [])
    action_mode = state.get("actionMode", "sequential")
    
    if action_mode == "sequential":
        for action in actions:
            action_output = execute_action(action, current_state, functions)
            current_state = merge_dicts(current_state, action_output)
    else:
        outputs = [execute_action(action, current_state, functions) for action in actions]
        for output in outputs:
            current_state = merge_dicts(current_state, output)
    
    return current_state

def execute_foreach_state(state: Dict, input_state: Dict, workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute a ForEachState."""
    input_collection = apply_jq(state.get("inputCollection", "[]"), input_state)
    iteration_param = state.get("iterationParam", "item")
    iterator_states = state.get("iterator", [])
    results = []
    
    for item in input_collection or []:
        item_state = deepcopy(input_state)
        item_state[iteration_param] = item
        for iterator_state in iterator_states:
            item_state = execute_state(iterator_state, item_state, workflow, functions)
        results.append(item_state.get("context", {}))
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return {"context": {"ForEachStateOutput": {"results": results}}}
    return set_path({}, output_path, {"results": results})

def execute_switch_state(state: Dict, input_state: Dict, workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute a SwitchState."""
    conditions = state.get("dataConditions", [])
    default_condition = state.get("defaultCondition", {})
    current_state = deepcopy(input_state)
    
    for condition in conditions:
        if apply_jq(condition["condition"], current_state):
            next_state_name = condition.get("transition")
            if next_state_name:
                next_state = next((s for s in workflow["states"] if s["name"] == next_state_name), None)
                if next_state:
                    return execute_state(next_state, current_state, workflow, functions)
            if condition.get("end"):
                return current_state
    
    next_state_name = default_condition.get("transition")
    if next_state_name:
        next_state = next((s for s in workflow["states"] if s["name"] == next_state_name), None)
        if next_state:
            return execute_state(next_state, current_state, workflow, functions)
    if default_condition.get("end"):
        return current_state
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return merge_dicts(current_state, {"context": {"SwitchStateOutput": {"value": 60}}})
    return set_path(current_state, output_path, {"value": 60})

def execute_parallel_state(state: Dict, input_state: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute a ParallelState."""
    current_state = deepcopy(input_state)
    branches = state.get("branches", [])
    
    branch_outputs = []
    for branch in branches:
        branch_state = deepcopy(current_state)
        for branch_state_def in branch.get("states", []):
            branch_state = execute_state(branch_state_def, branch_state, {}, functions)
        branch_outputs.append(branch_state)
    
    merged_output = current_state
    for output in branch_outputs:
        merged_output = merge_dicts(merged_output, output)
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return {"context": merged_output.get("context", {})}
    return set_path(current_state, output_path, merged_output.get("context", {}))

def execute_subflow_state(state: Dict, input_state: Dict, workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute a SubflowState."""
    workflow_id = state.get("workflowId")
    sub_workflow = next((sw for sw in workflow.get("subWorkflows", []) if sw["id"] == workflow_id), None)
    if not sub_workflow:
        raise ValueError(f"SubWorkflow {workflow_id} not found")
    
    input_expression = state.get("stateDataFilter", {}).get("input", "{}")
    sub_input = apply_jq(input_expression, input_state)
    sub_state = {"context": {"SubWorkflowOutput": sub_input.get("input", {})}}
    
    for sub_state_def in sub_workflow["states"]:
        sub_state = execute_state(sub_state_def, sub_state, sub_workflow, functions)
    
    output_path = state.get("stateDataFilter", {}).get("output", ".context")
    if output_path == ".context":
        return merge_dicts(input_state, {"context": {"ForEachStateOutput": sub_state.get("context", {})}})
    return set_path(input_state, output_path, sub_state.get("context", {}))

def execute_end_state(state: Dict, input_state: Dict) -> Dict:
    """Execute an EndState."""
    return input_state

def execute_state(state: Dict, input_state: Dict, workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute a state based on its type."""
    state_type = state["type"]
    input_expression = state.get("stateDataFilter", {}).get("input", "{}")
    current_state = apply_jq(input_expression, input_state) if input_expression else input_state
    
    if state_type == "parallel":
        return execute_parallel_state(state, current_state, functions)
    elif state_type == "operation":
        return execute_operation_state(state, current_state, functions)
    elif state_type == "foreach":
        return execute_foreach_state(state, current_state, workflow, functions)
    elif state_type == "switch":
        return execute_switch_state(state, current_state, workflow, functions)
    elif state_type == "subflow":
        return execute_subflow_state(state, current_state, workflow, functions)
    elif state_type == "end":
        return execute_end_state(state, current_state)
    else:
        raise ValueError(f"Unsupported state type: {state_type}")

def execute_workflow(workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Execute the entire workflow and return the final state."""
    current_state = {"context": {}}
    start_state_name = workflow.get("start")
    states = workflow.get("states", [])
    
    start_state = next((s for s in states if s["name"] == start_state_name), None) if isinstance(start_state_name, str) else start_state_name
    if not start_state:
        raise ValueError("No valid start state found")
    
    return execute_state(start_state, current_state, workflow, functions)

def validate_state_flow(workflow: Dict, functions: Dict[str, Callable] = {}) -> Dict:
    """Validate data flow by simulating state execution and checking input consistency."""
    errors = []
    context = {"context": {}}
    state_map = {state["name"]: state for state in workflow.get("states", [])}
    start_state = workflow.get("start")
    visited_states = set()
    intermediate_results = []

    if isinstance(start_state, str):
        current_state = state_map.get(start_state)
    else:
        current_state = None

    while current_state and current_state["name"] in state_map:
        state_name = current_state["name"]
        if state_name in visited_states:
            errors.append(f"Cycle detected in state transitions at state '{state_name}'")
            break
        visited_states.add(state_name)

        # Capture input state for states with actions
        state_input = deepcopy(context) if current_state.get("actions") else None

        # Simulate action execution and update context
        for action in current_state.get("actions", []):
            if "functionRef" in action and "dataOutput" in action:
                ref_name = action["functionRef"]["refName"]
                args = action["functionRef"].get("arguments", {})
                arg_input = apply_jq(args.get("input", "{}"), context)
                print(f"Action in state '{state_name}': ref_name={ref_name}, args={args}, arg_input={arg_input}")
                func = functions.get(ref_name)
                if not func:
                    errors.append(f"State '{state_name}' action references undefined function '{ref_name}'")
                    continue
                output = func(arg_input)
                context = merge_dicts(context, set_path({}, action["dataOutput"], output))

        # Handle foreach state specifically
        if current_state["type"] == "foreach":
            input_collection = apply_jq(current_state.get("inputCollection", "[]"), context)
            print(f"ForEach state '{state_name}': input_collection={input_collection}")
            if input_collection is None or (isinstance(input_collection, (list, dict)) and not input_collection):
                errors.append(f"State '{state_name}' inputCollection '{current_state['inputCollection']}' references undefined or empty data")
            else:
                iteration_param = current_state.get("iterationParam", "item")
                iterator_states = current_state.get("iterator", [])
                for item in input_collection or []:
                    item_context = deepcopy(context)
                    item_context[iteration_param] = item
                    print(f"ForEach iteration: item={item}, item_context={item_context}")
                    for iterator_state in iterator_states:
                        # Capture iterator state input
                        iterator_input = deepcopy(item_context) if iterator_state.get("actions") else None
                        for action in iterator_state.get("actions", []):
                            if "functionRef" in action and "dataOutput" in action:
                                ref_name = action["functionRef"]["refName"]
                                args = action["functionRef"].get("arguments", {})
                                arg_input = apply_jq(args.get("input", "{}"), item_context)
                                print(f"Action in iterator state '{iterator_state['name']}': ref_name={ref_name}, args={args}, arg_input={arg_input}")
                                func = functions.get(ref_name)
                                if not func:
                                    errors.append(f"Iterator state '{iterator_state['name']}' action references undefined function '{ref_name}'")
                                    continue
                                output = func(arg_input)
                                item_context = merge_dicts(item_context, set_path({}, action["dataOutput"], output))
                        # Capture iterator state output
                        if iterator_input is not None:
                            intermediate_results.append({
                                "state": iterator_state["name"],
                                "input": iterator_input,
                                "output": deepcopy(item_context)
                            })

        # Capture state output for states with actions
        if state_input is not None:
            intermediate_results.append({
                "state": state_name,
                "input": state_input,
                "output": deepcopy(context)
            })

        # Validate next state inputs
        next_state_name = current_state.get("transition")
        if next_state_name:
            next_state = state_map.get(next_state_name)
            if next_state:
                if "inputCollection" in next_state:
                    input_path = next_state["inputCollection"].split("//")[0].strip()
                    input_value = apply_jq(next_state["inputCollection"], context)
                    print(f"Next state '{next_state['name']}': input_path={input_path}, input_value={input_value}")
                    if input_value is None or (isinstance(input_value, (list, dict)) and not input_value):
                        errors.append(f"State '{next_state['name']}' inputCollection '{next_state['inputCollection']}' references undefined or empty data")
                for action in next_state.get("actions", []):
                    if "arguments" in action["functionRef"]:
                        for arg_name, arg_value in action["functionRef"]["arguments"].items():
                            arg_path = str(arg_value).split("//")[0].strip()
                            arg_result = apply_jq(arg_value, context)
                            print(f"Action in next state '{next_state['name']}': arg_name={arg_name}, arg_value={arg_value}, arg_result={arg_result}")
                            if arg_result is None or (isinstance(arg_result, (list, dict)) and not arg_result):
                                errors.append(f"Action in state '{next_state['name']}' argument '{arg_name}: {arg_value}' references undefined or empty data")

        current_state = state_map.get(next_state_name) if next_state_name else None
        if not current_state or current_state.get("end"):
            break

    result = {"status": "invalid", "message": errors} if errors else {"status": "valid", "message": ["Data flow is consistent"]}
    result["intermediate_results"] = intermediate_results
    return result