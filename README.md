CNCF Serverless Workflow Python v1.0
A Python 3 library for parsing, validating, and executing workflows defined in the CNCF Serverless Workflow v1.0 specification. This library supports all v1.0 state types (OperationState, ForEachState, SwitchState, SubflowState, ParallelState, EndState), JQ-based data filtering, and sub-workflows, optimized for agentic workflows and LLM-friendly design with structured comments.
Features

Parse and Validate: Load and validate YAML/JSON workflows against the v1.0 schema.
Execute Workflows: Full support for all state types, including parallel execution, iteration, conditional transitions, and sub-workflows.
JQ Integration: Evaluates JQ expressions for stateDataFilter, arguments, and inputCollection.
Robust Merging: Correctly merges state outputs (e.g., ParallelState into .context) with null checks.
Structured Comments: Workflow includes # Input: <JSON> | Output: <JSON> comments for states and actions to aid LLMs and developers.

Installation

Clone the repository:git clone https://github.com/<your-username>/cncf-serverless-workflow-python-v1.git
cd cncf-serverless-workflow-python-v1


Install dependencies:pip install pyyaml jq jsonschema



Usage

Save your workflow (e.g., workflow.yaml) and schema (workflow-schema.yaml).
Run the engine:from workflow_engine_v1 import load_workflow, validate_workflow, execute_workflow

with open("workflow-schema.yaml", "r") as f:
    schema = load_workflow(f.read())
with open("workflow.yaml", "r") as f:
    workflow = load_workflow(f.read())

validate_workflow(workflow, schema)
final_state = execute_workflow(workflow)
print(json.dumps(final_state, indent=2))


Example output for the provided workflow (simplified-agentic-workflow.yaml):{
  "context": {
    "ParallelStartOutput": {
      "items": [
        {"value": 60},
        {"value": 30},
        {"value": 45}
      ],
      "value": 60,
      "Branch1Output": 62,
      "Branch2Output": "Processed: 2"
    },
    "ForEachStateOutput": {
      "results": [
        {"method2": "Processed: 10"},
        {"method3": [31, 32]},
        {"method3": [46, 47]}
      ]
    },
    "SwitchStateOutput": {"value": 60},
    "OperationStateOutput": {
      "initOperation": {"value": 70},
      "method1": 72,
      "method2": "Processed: Seq2: 72",
      "method3": ["Processed: Seq2: 72", "Processed: Seq2: 73"],
      "method4": {"key": "Processed: Seq2: 72"}
    }
  }
}



Project Structure

workflow_engine_v1.py: Core engine for parsing, validating, and executing workflows.
workflow-schema.yaml: CNCF Serverless Workflow v1.0 schema for validation.
simplified-agentic-workflow.yaml: Example workflow with structured comments for states and actions.

Extending the Engine

Custom Functions: Add to FUNCTIONS dictionary in workflow_engine_v1.py (e.g., HTTP-based functions).
Error Handling: Enhance with try-catch blocks and logging for production use.
Testing: Add unit tests for edge cases (e.g., null inputs, invalid JQ expressions).

Contributing

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.

License
MIT License. See LICENSE for details.
Acknowledgments

Built on the CNCF Serverless Workflow v1.0 specification.
Inspired by serverlessworkflow/sdk-python (v0.8).
