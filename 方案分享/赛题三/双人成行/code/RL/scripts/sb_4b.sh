#!/bin/bash
set -x

# Configuration through environment variables
# Set these variables before running:
export PROJECT_HOME="path/to/ShorterBetter"
export LOG_DIR="${PROJECT_HOME}/logs"

# ----------------------------------------
# To change the reward function hyperparameters, please change the alpha and beta in the following:
# /ShorterBetter/verl/verl/workers/reward_manager/naive.py line 244
# By default, alpha=2.0, beta=0.001
# ----------------------------------------

# ----------------------------------------
# The training process will print out the output lengths and correct counts for each batch.
# You can use check_acc_len.py to plot the accuracy and output length trends.
# ----------------------------------------


# Warning: Export VLLM_ATTENTION_BACKEND on every machine before starting Ray cluster.
# vLLM without XFORMERS will results in CUDA errors.
export PYTHONPATH="${PROJECT_HOME}:$PYTHONPATH"
export VLLM_ATTENTION_BACKEND=XFORMERS
export WANDB_API_KEY="xxx"
export WANDB_MODE=offline
export WANDB_DIR="${PROJECT_HOME}/wandb"
# ----------------------------------------

# Default model path if not specified
MODEL_PATH=${MODEL_PATH:-"path/to/Qwen3-4B"}
# Train over a single node, 8 H200-140GB GPUs.
python3 -m verl.trainer.main_ppo \
    algorithm.adv_estimator=grpo \
    data.train_files=xxx/train.parquet \
    data.train_batch_size=128 \
    data.shuffle=False \
    data.filter_overlong_prompts=True \
    data.max_prompt_length=800 \
    data.max_response_length=8000 \
    actor_rollout_ref.model.path=$MODEL_PATH \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.actor.ppo_mini_batch_size=16 \
    actor_rollout_ref.actor.use_dynamic_bsz=True \
    actor_rollout_ref.actor.ppo_max_token_len_per_gpu=16384 \
    actor_rollout_ref.actor.use_kl_loss=True \
    actor_rollout_ref.actor.kl_loss_coef=0.001 \
    actor_rollout_ref.actor.kl_loss_type=low_var_kl \
    actor_rollout_ref.actor.ulysses_sequence_parallel_size=1 \
    actor_rollout_ref.model.enable_gradient_checkpointing=True \
    actor_rollout_ref.actor.fsdp_config.param_offload=True \
    +actor_rollout_ref.actor.fsdp_config.grad_offload=True \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=True \
    actor_rollout_ref.rollout.tensor_model_parallel_size=2 \
    actor_rollout_ref.rollout.name=vllm \
    actor_rollout_ref.rollout.temperature=1.0 \
    +actor_rollout_ref.rollout.val_temperature=1.0 \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.85 \
    actor_rollout_ref.rollout.n=8 \
    +actor_rollout_ref.rollout.n_val=8 \
    actor_rollout_ref.ref.fsdp_config.param_offload=True \
    algorithm.kl_ctrl.kl_coef=0.001 \
    trainer.critic_warmup=0 \
    trainer.logger="[console, wandb]" \
    trainer.project_name='ShorterBetter' \
    trainer.experiment_name='AFAC_submit' \
    +trainer.val_before_train=False \
    trainer.n_gpus_per_node=8 \
    trainer.nnodes=1 \
    trainer.save_freq=100 \
    trainer.test_freq=-1 \
    trainer.default_hdfs_dir=null \
    trainer.total_epochs=1 2>&1 | tee ${LOG_DIR}/finance.log