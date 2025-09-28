"""
GRPO微调模型的第一步:无COT模型下的微调
"""
from transformers import AutoTokenizer, AutoModelForCausalLM,BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer
from peft import LoraConfig, get_peft_model, TaskType
from LLM_Train.dataset import GRPODataset
from LLM_Train.rewards import sentiment_reward
from transformers import TrainerCallback

class RewardLoggingCallback(TrainerCallback):
    def on_evaluate(self, args, state, control, **kwargs):
        model = kwargs.get("model")
        reward_funcs = kwargs.get("reward_funcs")
    def on_step_end(self, args, state, control, **kwargs):
        rewards = kwargs.get("rewards", [])
        if rewards:
            avg_reward = sum(rewards) / len(rewards)
            with open("rewards_log.txt", "a") as f:
                f.write(f"Step {state.global_step}: Average Reward = {avg_reward}\n")

if __name__ == '__main__':
    # 读入预训练模型
    model_name = "Qwen3-4B"
    model = AutoModelForCausalLM.from_pretrained(model_name)
    # LoRA配置参数
    lora_config = LoraConfig(
        r=4,  
        lora_alpha=128,  
        target_modules=["q_proj", "k_proj", "v_proj","o_proj"],
        lora_dropout=0.1, 
        task_type=TaskType.CAUSAL_LM
    )
    # 使用LoRA方法训练模型
    model = get_peft_model(model, lora_config)
    model.cuda()
    # 打印可训练参数信息
    model.print_trainable_parameters()
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # 设置模型输出目录
    output_dir="LLM_Train/output"
    # GRPO训练参数配置
    training_args = GRPOConfig(
        output_dir=output_dir,
        learning_rate=1e-5,
        adam_beta1 = 0.9,
        adam_beta2 = 0.99,
        weight_decay = 0.1,
        warmup_ratio = 0.1,
        lr_scheduler_type='cosine',
        logging_steps=1,
        bf16=True,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=6,
        num_generations=6,
        max_prompt_length=512,
        max_completion_length=256,
        num_train_epochs=1,
        save_steps=100,
        max_grad_norm=0.1,
        log_on_each_node=False,
        use_vllm=False,
        report_to="none",
    )
    # 加载训练数据集
    dataset = GRPODataset('Data/CFSC-ABSA/json格式/train.txt')
    # 初始化GRPO训练器
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[sentiment_reward],
        args=training_args,
        train_dataset=dataset,
         callbacks=[RewardLoggingCallback()]
    )
    # 开始训练
    trainer.train(resume_from_checkpoint=False)
    trainer.save_model(output_dir)
    