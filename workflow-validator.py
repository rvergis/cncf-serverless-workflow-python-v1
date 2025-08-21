import yaml
import jsonschema
import json
from typing import Dict

def load_yaml(file_path: str) -> Dict:
    """Load YAML file into a dictionary."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def validate_workflow(workflow: Dict, schema: Dict) -> Dict:
    """Validate workflow against schema, checking mandatory fields."""
    try:
        # Validate against JSON schema
        jsonschema.validate(workflow, schema)
        
        # Additional checks for mandatory transition/end and iterator states
        for state in workflow.get("states", []):
            state_name = state["name"]
            state_type = state["type"]
            
            # Check for mandatory transition or end (except EndState and SwitchState)
            if state_type != "end" and not (state.get("transition") or state.get("end")):
                if state_type != "switch" or not (state.get("dataConditions") or state.get("defaultCondition")):
                    raise ValueError(f"State '{state_name}' missing mandatory transition or end: true")
            
            # Check for mandatory stateDataFilter (except EndState)
            if state_type != "end" and not state.get("stateDataFilter"):
                raise ValueError(f"State '{state_name}' missing mandatory stateDataFilter with input and output")
            
            # Check for mandatory dataOutput in actions
            for action in state.get("actions", []):
                if not action.get("dataOutput"):
                    raise ValueError(f"Action in state '{state_name}' missing mandatory dataOutput")
            
            # Check iterator states in ForEachState
            if state_type == "foreach":
                for iterator_state in state.get("iterator", []):
                    if iterator_state["type"] == "end":
                        raise ValueError(f"Iterator state '{iterator_state['name']}' cannot be type: end; use OperationState or SubflowState with end: true")
                    if not (iterator_state.get("transition") or iterator_state.get("end") or iterator_state.get("dataConditions")):
                        raise ValueError(f"Iterator state '{iterator_state['name']}' missing mandatory transition or end: true")
                    if not iterator_state.get("stateDataFilter"):
                        raise ValueError(f"Iterator state '{iterator_state['name']}' missing mandatory stateDataFilter")
        
        # Validate sub-workflows
        for sub_workflow in workflow.get("subWorkflows", []):
            validate_workflow(sub_workflow, schema)
        
        return {"status": "valid", "message": "Workflow is valid"}
    
    except jsonschema.exceptions.ValidationError as e:
        return {"status": "invalid", "message": f"Schema validation failed: {str(e)}"}
    except ValueError as e:
        return {"status": "invalid", "message": str(e)}

def main():
    # Load schema and workflow
    schema = load_yaml("workflow-schema.yaml")
    workflow = load_yaml("simplified-agentic-workflow.yaml")
    
    # Validate
    result = validate_workflow(workflow, schema)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()