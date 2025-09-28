# 8 * 80GiB
export NODE_RANK=${RANK:-0}
export MASTER_ADDR=${MASTER_ADDR:-localhost}
export MASTER_PORT=${MASTER_PORT:-22}
NPROC_PER_NODE=8 \
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
swift sft \
    --model xxx/Qwen3-4B \
    --train_type full \
    --dataset 'xxx/train.json' \
    --split_dataset_ratio 0 \
    --torch_dtype bfloat16 \
    --per_device_train_batch_size 2 \
    --learning_rate 4e-5 \
    --gradient_accumulation_steps 2 \
    --logging_steps 5 \
    --max_length 20000 \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 8 \
    --dataset_num_proc 8 \
    --num_train_epochs 3 \
    --save_strategy epoch \
    --save_steps 1 \
    --save_total_limit 3 \
    --save_only_model true \
    --output_dir xxx/output/Qwen3-4B \
    --deepspeed zero3_offload \
    --attn_impl flash_attn \
    --system ""
    # --dataset_shuffle False
