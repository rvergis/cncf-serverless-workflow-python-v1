# CNCF Serverless Workflow Python v1.0

A Python 3 library for parsing, validating, and executing workflows defined in the [CNCF Serverless Workflow v1.0 specification](https://serverlessworkflow.io/). Supports all state types (`OperationState`, `ForEachState`, `SwitchState`, `SubflowState`, `ParallelState`, `EndState`, `EventState`, `DelayState`, `InjectState`), JQ-based data filtering, events, retries, and authentication. Optimized for agentic workflows with LLM-friendly design.

## Features
- **Parse and Validate**: Validates YAML/JSON workflows against the v1.0 schema, enforcing `transition` or `end: true` for non-`EndState` types, collecting all errors.
- **Execute Workflows**: Handles all state types, including event-driven, delay, and data injection.
- **JQ Integration**: Supports JQ for `stateDataFilter`, `arguments`, and `inputCollection`.
- **LLM-Friendly**: Structured comments (e.g., `# MANDATORY Transition`) and comprehensive error reporting for LLM generation.
- **Testing**: Pytest suite for validation of multiple error cases.

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/<your-username>/cncf-serverless-workflow-python-v1.git
   cd cncf-serverless-workflow-python-v1
   ```
2. Install dependencies:
   ```
   pip install pyyaml jq jsonschema pytest
   ```
3. Install as a package:
   ```
   pip install .
   ```

## Usage
1. Save your workflow (`workflow.yaml`) and schema (`workflow-schema.yaml`).
2. Validate and execute:
   ```python
   from validate_workflow import load_yaml, validate_workflow
   from workflow_engine_v1 import execute_workflow

   schema = load_yaml("workflow-schema.yaml")
   workflow = load_yaml("workflow.yaml")
   
   result = validate_workflow(workflow, schema)
   if result["status"] == "valid":
       final_state = execute_workflow(workflow)
       print(json.dumps(final_state, indent=2))
   else:
       print(json.dumps(result["message"], indent=2))
   ```
3. Example output for `simplified-agentic-workflow.yaml`:
   ```json
   {
     "context": {
       "ParallelStartOutput": {
         "items": [{"value": 60}, {"value": 30}, {"value": 45}],
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
   ```

## LLM Integration
To generate valid workflows:
1. Provide `simplified-agentic-workflow.yaml` as a one-shot example.
2. Use prompt: “Generate a state with `transition` (to ParallelStart, ForEachState, etc.) or `end: true` after `type`, optional `stateDataFilter`, and `dataOutput`.”
3. Validate with `validate_workflow.py`, retrying up to 3 times with errors: “Regenerate fixing: {errors}.”
4. Example error: `["State 'GetAllObjectIds' missing mandatory transition or end: true"]`.

## Testing
Run tests to validate workflows:
```
pytest test_validate_workflow.py
```

## Project Structure
- `workflow_engine_v1.py`: Executes workflows.
- `validate_workflow.py`: Validates workflows, collecting all errors.
- `test_validate_workflow.py`: Pytest suite for multiple error cases.
- `workflow-schema.yaml`: Full CNCF v1.0 schema.
- `simplified-agentic-workflow.yaml`: Example workflow with LLM-friendly comments.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
MIT License. See [LICENSE](LICENSE).

## Acknowledgments
- Built on CNCF Serverless Workflow v1.0.
- Inspired by `serverlessworkflow/sdk-python` (v0.8).