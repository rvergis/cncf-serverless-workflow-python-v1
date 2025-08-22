import yaml
import jsonschema
from jsonschema import Draft7Validator
import json
from typing import Dict, List, Union, TextIO
from pathlib import Path

def load_yaml(file: Union[str, bytes, Path, TextIO]) -> dict:
    """Load YAML from a file path or file-like object."""
    if isinstance(file, (str, bytes, Path)):
        with open(file, 'r') as f:
            return yaml.safe_load(f)
    return yaml.safe_load(file)  # Handle file-like object (e.g., TextIOWrapper)

def validate_workflow(workflow: Dict, schema: Dict) -> Dict:
    """Validate workflow against schema, collecting all errors."""
    errors: List[str] = []

    # Collect JSON schema validation errors with detailed parsing
    validator = Draft7Validator(schema)
    for error in validator.iter_errors(workflow):
        path = ".".join(str(p) for p in error.path)
        if error.validator == "oneOf" and "states" in path:
            state_idx = int(path.split(".")[1]) if path.split(".")[1].isdigit() else 0
            state = workflow.get("states", [])[state_idx]
            state_type = state.get("type")
            if state_type and state_type != "end" and not (state.get("transition") or state.get("end")):
                errors.append(f"State '{state.get('name', f'state at {path}')} missing mandatory transition or end: true")
        else:
            errors.append(f"Schema validation failed: {error.message} at {path} - Check required fields or structure")

    # Custom checks for spec-specific rules (iterator constraints and dataOutput enforcement)
    for state in workflow.get("states", []):
        state_name = state["name"]
        state_type = state["type"]

        # Check iterator states in ForEachState
        if state_type == "foreach":
            for iterator_state in state.get("iterator", []):
                iter_name = iterator_state["name"]
                if iterator_state["type"] == "end":
                    errors.append(f"Iterator state '{iter_name}' cannot be type: end; use end: true")
                if not (iterator_state.get("transition") or iterator_state.get("end") or iterator_state.get("dataConditions")):
                    errors.append(f"Iterator state '{iter_name}' missing mandatory transition or end: true")

        # Enforce dataOutput for actions to ensure result storage
        if state_type in ["operation", "foreach", "subflow"]:
            for action in state.get("actions", []):
                if "functionRef" in action and not action.get("dataOutput"):
                    errors.append(f"Action in state '{state_name}' missing dataOutput - Result of '{action['functionRef'].get('refName', 'unknown function')}' will be discarded unless stored. Consider adding dataOutput (e.g., '.context.{state_name}Output')")

    # Validate sub-workflows, avoiding prefix for valid cases
    for sub_workflow in workflow.get("subWorkflows", []):
        sub_errors = validate_workflow(sub_workflow, schema).get("message", [])
        if sub_errors and sub_errors != ["Workflow is valid"]:
            errors.extend([f"Sub-workflow '{sub_workflow['id']}': {msg}" for msg in sub_errors if msg])
        elif sub_errors:
            errors.extend(sub_errors)  # Use unprefixed message for valid sub-workflows

    if errors and errors != ["Workflow is valid"]:
        return {"status": "invalid", "message": errors}
    return {"status": "valid", "message": ["Workflow is valid"]}

def main():
    schema = load_yaml("workflow_schema.yaml")
    workflow = load_yaml("workflow_example.yaml")
    result = validate_workflow(workflow, schema)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()