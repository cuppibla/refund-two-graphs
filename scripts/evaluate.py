"""Run ADK's eval CLI with explicit gcloud credentials for the judge.

The registry alias changes credential configuration, not the actual model.
No environment or application-default credentials are overwritten.
"""
import json
import shutil

from google.adk.cli.cli_tools_click import main
from google.adk.models.google_llm import Gemini
from google.adk.models.registry import LLMRegistry

from app.config import MODEL, PROJECT, ROOT
from app.credentials import GcloudCredentials


class RefundDemoJudge(Gemini):
    @classmethod
    def supported_models(cls):
        return [r'^refund_demo_judge$']

    def __init__(self, model='refund_demo_judge', **kwargs):
        super().__init__(model=MODEL, client_kwargs={
            'vertexai': True, 'project': PROJECT, 'location': 'global',
            'credentials': GcloudCredentials(),
        }, **kwargs)

    async def generate_content_async(self, llm_request, stream=False):
        # The evaluator also puts its registry alias on the request itself.
        request = llm_request.model_copy(update={'model': MODEL})
        async for response in super().generate_content_async(request, stream=stream):
            yield response


if __name__ == '__main__':
    LLMRegistry.register(RefundDemoJudge)
    main([
        'eval', './eval_entry', 'tests/eval/evalsets/basic.evalset.json',
        '--config_file_path', 'tests/eval/eval_config.json',
        '--print_detailed_results',
    ], standalone_mode=False)
    latest = max((ROOT / 'eval_entry/.adk/eval_history').glob('*.evalset_result.json'),
                 key=lambda path: path.stat().st_mtime)
    shutil.copyfile(latest, ROOT / 'evidence/adk-eval-result.json')
    results = json.loads(latest.read_text())['eval_case_results']
    if len(results) != 2 or any(result['final_eval_status'] != 1 for result in results):
        raise RuntimeError('ADK evaluation did not pass both reply cases; inspect evidence/adk-eval-result.json.')
