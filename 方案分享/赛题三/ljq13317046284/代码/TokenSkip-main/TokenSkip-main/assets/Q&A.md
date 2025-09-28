# Q&A

This page contains frequently asked questions about the re-implementation of TokenSkip.

#### 1.Choice of Delimiter

We use the `eos_token` from LLaMA-3.1-8B, which is `<|eot_id|>`, as the delimiter token for all experiments.  The format follows: `<|eot_id|>compression_ratio<|eot_id|>`. This delimiter clearly separates the compression ratio from the surrounding context.

The choice of delimiter does not affect the performance of TokenSkip, and you are free to select a unique delimiter of your own.

#### 2.Usage of vLLM

In our early-stage experiments, we observed that when using vLLM, the outputs of LLMs varied even when the same seed was used. To ensure stable reproducibility, we exclusively adopt the `transformers` implementation in our code. 

However, we note that TokenSkip only appends `compression_ratio` to the end of the input. Given this minimal modification, TokenSkip supports vLLM, and you can adapt it to [vLLM's implementation](https://github.com/deepseek-ai/DeepSeek-Math/blob/main/evaluation/infer/run_cot_eval.py#L75) as needed.

#### 3.Answer Format

TokenSkip is designed to controllably compress the *Chain-of-Thought* or *thinking* portion (enclosed within `<\think><\think>`) of LLMs while preserving the *summary/answer* part unchanged. 

In our experiments, we observed that most answer outputs from LLaMA-3.1-8B follow the format: `\n\nThe final answer is:`. To maintain consistency, we retain this pattern in our [implementation](https://github.com/hemingkx/TokenSkip/blob/main/LLMLingua.py#L51) and adopt the same format for the Qwen series. However, you are free to modify the answer format as needed.