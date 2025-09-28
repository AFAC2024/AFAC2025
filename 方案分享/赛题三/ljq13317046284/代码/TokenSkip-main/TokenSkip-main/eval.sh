BENCHMARK="afac" # "gsm8k", "math", "afac"
OUPTUT_DIR="outputs/Qwen3-4B/${BENCHMARK}/"
MODEL_PATH="/your_model_path/Qwen3-4B"
MODEL_SIZE="7b"
MODEL_TYPE="qwen" # "llama3", "qwen"
DATA_TYPE="test" # "train", "test"

# Generation Settings
MAX_NUM_EXAMPLES=100000000000000
MAX_NEW_TOKENS=512 # 512 for gsm8k, 1024 for math
EVAL_BATCH_SIZE=16
TEMPERATURE=0.0
SEED=42

# TokenSkip Settings
ADAPTER_PATH="/your_model_path/TokenSkip-Qwen3-4B-${BENCHMARK}"
COMPRESSION_RATIO=0.5


CUDA_VISIBLE_DEVICES=0 python ./evaluation.py --output-dir ${OUPTUT_DIR} --model-path ${MODEL_PATH} --tokenizer-path ${MODEL_PATH} \
    --model-size ${MODEL_SIZE} --model-type ${MODEL_TYPE} --data-type ${DATA_TYPE}  --max_num_examples ${MAX_NUM_EXAMPLES} \
    --max_new_tokens ${MAX_NEW_TOKENS} --eval_batch_size ${EVAL_BATCH_SIZE} --temperature ${TEMPERATURE} --seed ${SEED} --benchmark ${BENCHMARK} --use_vllm \
    --adapter-path ${ADAPTER_PATH} --compression_ratio ${COMPRESSION_RATIO} --use_adapter