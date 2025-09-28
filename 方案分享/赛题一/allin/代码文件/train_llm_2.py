"""
GRPO微调模型的第二步:开启COT情况下的微调
"""
from peft import PeftModel
from transformers import AutoTokenizer, AutoModelForCausalLM,BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer
from peft import LoraConfig, get_peft_model, TaskType
from LLM_Train.dataset import GRPODataset
from LLM_Train.rewards import sentiment_reward

if __name__ == '__main__':
    # 基础模型和微调模型路径配置
    base_model = "Qwen3-4B" 
    # 使用第一轮无COT训练得到的第500轮的checkpoint文件，在此基础上开始训练
    # 但是由于GRPOTrainer参数设置不同，并没有使用resume_from_checkpoint=True继续训练，而是又在新的数据上从头开始训练
    peft_model = "LLM_Train/output/checkpoint-500"
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token
    # 加载基础模型并指定设备映射到GPU 0
    model = AutoModelForCausalLM.from_pretrained(base_model, device_map = "cuda:0")
    # 加载之前训练的LoRA权重
    model = PeftModel.from_pretrained(model, peft_model)
    # 冻结非LoRA参数，只训练LoRA参数
    for name, param in model.named_parameters():
        if "lora" not in name.lower():
            param.requires_grad = False
        else:
            param.requires_grad = True
    # 打印所有可训练的参数名称
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(name)
    model.cuda()
    model.print_trainable_parameters()
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    # 设置模型输出目录
    output_dir="LLM_Train/cot_ouput"
    # GRPO训练参数配置（针对COT场景降低显存要求）
    training_args = GRPOConfig(
        output_dir=output_dir,
        learning_rate=1e-6,
        adam_beta1 = 0.9,
        adam_beta2 = 0.99,
        weight_decay = 0.1,
        warmup_ratio = 0.1,
        lr_scheduler_type='cosine',
        logging_steps=1,
        bf16=True,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=6,
        num_generations=3,
        max_prompt_length=512,
        max_completion_length=1024,
        num_train_epochs=1,
        save_steps=10,
        max_grad_norm=0.1,
        log_on_each_node=False,
        use_vllm=False,
        report_to="none",
    )
    # 加载训练数据集，启用COT模式
    dataset = GRPODataset('Data/CFSC-ABSA/json格式/test.txt',cot=True)
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[sentiment_reward],
        args=training_args,
        train_dataset=dataset
    )
    trainer.train(resume_from_checkpoint=False)
    trainer.save_model(output_dir)
    