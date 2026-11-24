# Switch models

Neither agent hard-codes a Claude model, and the Gemini model can be overridden.

## Claude

`CLAUDE_MODEL` is required. Set it to any current Claude model id:

```bash
export CLAUDE_MODEL=claude-opus-5-5      # most capable Opus
export CLAUDE_MODEL=claude-sonnet-5-5    # faster, lower cost
export CLAUDE_MODEL=claude-haiku-5-5     # fastest, lowest cost
```

To see the ids your key can use:

```bash
python -c "import anthropic; [print(m.id) for m in anthropic.Anthropic().models.list()]"
```

An unknown id gives `Model '...' not found: check CLAUDE_MODEL.`

## Gemini

`GEMINI_MODEL` is optional and defaults to `gemini-3.6-flash`. Set it to any Gemini
model id that supports function calling:

```bash
export GEMINI_MODEL=your-gemini-model-id
```

To see the ids your key can use:

```bash
python -c "from google import genai; [print(m.name) for m in genai.Client().models.list()]"
```

## Compare models on the same requests

Running the agent by hand shows one request at a time. To compare models properly, run
the eval once per model and compare the summaries:

```bash
CLAUDE_MODEL=claude-opus-5-5   python evals/run_evals.py --models claude --out evals/results/opus.json
CLAUDE_MODEL=claude-haiku-5-5  python evals/run_evals.py --models claude --out evals/results/haiku.json
```

See [Run the eval](run-the-eval.md) for how to read the results.

## Related

- [Run the eval](run-the-eval.md)
- [Troubleshooting: setup and keys](../troubleshooting.md#setup-and-keys)
- [Claude and Gemini side by side](../PORTING.md)
