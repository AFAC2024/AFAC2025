CUDA_VISIBLE_DEVICES=7 \
swift export \
    --adapters eval_model/qwen2.5-14b/checkpoint-885 \
    --merge_lora true
