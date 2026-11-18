# Refund reply evaluation

Run `make eval` from the project root. The wrapper invokes ADK's evaluation CLI with an explicit-credential judge mapped to the configured Gemini model.

`basic.evalset.json` contains the decided cases from the successful approval and decline workflow runs. It evaluates the same response-agent factory used by the Workflow, isolated from database execution.

The three rubrics check decision/order/amount, grounding in the supplied review note, and the boundary between an approval and an executed payment. Both cases must score 1.0. Results are saved to `evidence/adk-eval-result.json`.

These two model-judged cases do not validate orchestration or establish broad reliability. See the separate offline tests and live execution records for the workflow evidence.
