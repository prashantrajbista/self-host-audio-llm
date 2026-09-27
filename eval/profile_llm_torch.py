"""Phase 5: torch.profiler trace of vLLM offline inference (kernel-level, CPU+CUDA activity).

Runs vLLM's Python API directly (not the HTTP server) so torch.profiler can see real ops —
profiling through the OpenAI-compatible HTTP server only measures client-side wall time, since
the model runs in a separate process. Must run directly on the GPU box with `pip install vllm`
(not inside the gateway/stt/tts containers, and not on this dev Mac — no CUDA here).

Run: python -m eval.profile_llm_torch --model Qwen/Qwen2.5-1.5B-Instruct --out eval/results
"""

import argparse

from torch.profiler import ProfilerActivity, profile

PROMPTS = [
    "What is the capital of France?",
    "Explain what a WebSocket is in one sentence.",
    "Write a haiku about GPUs.",
]


def main(model: str, out_dir: str):
    from vllm import LLM, SamplingParams

    llm = LLM(model=model, dtype="auto")
    sampling = SamplingParams(max_tokens=128)

    llm.generate(["warmup"], sampling)  # exclude first-call compile/setup cost from the trace

    with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], record_shapes=True) as prof:
        llm.generate(PROMPTS, sampling)

    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))
    trace_path = f"{out_dir}/vllm_trace.json"
    prof.export_chrome_trace(trace_path)
    print(f"chrome trace written to {trace_path} (open in chrome://tracing or Perfetto)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--out", default="eval/results")
    args = parser.parse_args()
    main(args.model, args.out)
