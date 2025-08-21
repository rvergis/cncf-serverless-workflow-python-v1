import yaml
import jsonschema
from jsonschema import Draft7Validator
import json
from typing import Dict, List

def load_yaml(file_path: str) -> Dict:
    """Load YAML file into a dictionary."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def validate_workflow(workflow: Dict, schema: Dict) -> Dict:
    """Validate workflow against schema, collecting all errors."""
    errors: List[str] = []

    # Collect JSON schema validation errors
    validator = Draft7Validator(schema)
    for error in validator.iter_errors(workflow):
        errors.append(f"Schema validation failed: {error.message} at {'.'.join(str(p) for p in error.path)}")

    # Custom checks for mandatory fields
    for state in workflow.get("states", []):
        state_name = state["name"]
        state_type = state["type"]

        # Check transition or end (except EndState and SwitchState)
        if state_type != "end" and not (state.get("transition") or state.get("end")):
            if state_type != "switch" or not (state.get("dataConditions") or state.get("defaultCondition")):
                errors.append(f"State '{state_name}' missing mandatory transition or end: true")

        # Check stateDataFilter (except EndState)
        if state_type != "end" and not state.get("stateDataFilter"):
            errors.append(f"State '{state_name}' missing mandatory stateDataFilter with input and output")

        # Check dataOutput in actions
        for action in state.get("actions", []):
            if not action.get("dataOutput"):
                errors.append(f"Action in state '{state_name}' missing mandatory dataOutput")

        # Check iterator states in ForEachState
        if state_type == "foreach":
            for iterator_state in state.get("iterator", []):
                iter_name = iterator_state["name"]
                if iterator_state["type"] == "end":
                    errors.append(f"Iterator state '{iter_name}' cannot be type: end; use end: true")
                if not (iterator_state.get("transition") or iterator_state.get("end") or iterator_state.get("dataConditions")):
                    errors.append(f"Iterator state '{iter_name}' missing mandatory transition or end: true")
                if not iterator_state.get("stateDataFilter"):
                    errors.append(f"Iterator state '{iter_name}' missing mandatory stateDataFilter")

    # Validate sub-workflows
    for sub_workflow in workflow.get("subWorkflows", []):
        sub_errors = validate_workflow(sub_workflow, schema).get("message", [])
        errors.extend([f"Sub-workflow '{sub_workflow['id']}': {msg}" for msg in sub_errors if msg])

    if errors:
        return {"status": "invalid", "message": errors}
    return {"status": "valid", "message": ["Workflow is valid"]}

def main():
    schema = load_yaml("workflow-schema.yaml")
    workflow = load_yaml("simplified-agentic-workflow.yaml")
    result = validate_workflow(workflow, schema)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()