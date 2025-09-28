CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
NPROC_PER_NODE=8 \
swift sft \
    --model /mnt/model/Qwen2.5-14B-Instruct-1M \
    --train_type lora \
    --dataset sft_train.json \
    --torch_dtype bfloat16 \
    --per_device_train_batch_size 1 \
    --learning_rate 1e-5 \
    --gradient_accumulation_steps 1 \
    --packing true \
    --rope_scaling yarn \
    --max_length 100000 \
    --save_steps 100 \
    --logging_steps 5 \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 8 \
    --dataset_num_proc 8 \
    --save_total_limit 1 \
    --use_liger_kernel true \
    --save_only_model true \
    --deepspeed zero3 \
    --attn_impl flash_attn \
    --sequence_parallel_size 8 \
    --add_version false \
    --output_dir output/qwen2.5-14b \
    --split_dataset_ratio 0 \
    --num_train_epochs 3