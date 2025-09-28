from transformers import (
    AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments,
    TrainerCallback, TrainerState, TrainerControl
)
from peft import PeftModel, get_peft_model, LoraConfig, TaskType
from evaluator import AccEvaluator
import torch
from trl import DPOTrainer, DPOConfig
from utils import read_jsonl, save_to_jsonl, token_measure
import argparse
import time
import os
from datasets import Dataset
import setproctitle
import logging
import json
from vllm import LLM, SamplingParams
from tqdm import tqdm

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
proc_title = "your_proc_name"
setproctitle.setproctitle(proc_title)
SEED = 1024

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class LoggingCallback(TrainerCallback):
    """
    Custom callback for logging training history to JSONL files.
    
    This callback saves the training history to a specified JSONL file
    whenever logging occurs during training.
    """
    
    def __init__(self, log_file):
        """
        Initialize the callback with a log file path.
        
        Args:
            log_file: Path to save the training logs
        """
        self.log_file = log_file

    def on_log(self, local_args, state: TrainerState, control: TrainerControl, **kwargs):
        """
        Save training history when logging occurs.
        
        Args:
            local_args: Local arguments passed to the callback
            state: Current trainer state
            control: Trainer control object
            **kwargs: Additional keyword arguments
        """
        save_to_jsonl(state.log_history, self.log_file)


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default=None,
                        help='The base model name.')
    parser.add_argument("--lora_path", default=None, help="The path for lora model")
    parser.add_argument("--train_data_path", default=None, help="The path for loaded data")
    parser.add_argument("--test_data_path", default=None, help="The path for loaded data")

    # Saving details
    parser.add_argument("--output_dir", default=None,
                        help="The output directory")
    parser.add_argument("--strategy", default="lora", help="dpo, lora")
    parser.add_argument("--save", action='store_true', help="If we save the finetuned model.")
    parser.add_argument("--eval", action='store_true', help="If we just eval the model.")

    # Training details
    parser.add_argument("--batch_size", default=64, type=int, help="=The batch size for training.")
    parser.add_argument("--epoch", default=2, type=int, help="=The training epochs.")
    parser.add_argument("--lr", default=1e-3, type=float, help="=The training learning detail.")
    parser.add_argument("--max_new_tokens", default=512, type=int, help="=The max new tokens for training.")
    return parser.parse_args()


def inference_eval(sample_list, base_model_path, lora_path, batch_size):
    """
    Run inference evaluation using vLLM with a fine-tuned model.
    
    Args:
        sample_list: List of input samples to evaluate
        base_model_path: Path to the base model
        lora_path: Path to LoRA weights
        batch_size: Batch size for inference
        
    Returns:
        list: List of model predictions for each input sample
    """
    logger.info("Inference evaluating with vLLM...")
    logger.info("Loading Base Model...")
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,
        device_map="cpu"  
    )
    logger.info("Loading LoRA Weights...")
    model = PeftModel.from_pretrained(model, lora_path)
    logger.info("Merging LoRA with Base Model...")
    model = model.merge_and_unload()

    merged_model_path = './.cache/merged_model'  
    model.save_pretrained(merged_model_path)

    llm = LLM(
        model=merged_model_path,
        tokenizer=base_model_path,
        gpu_memory_utilization=0.25,
        max_model_len=1024,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, local_files_only=True)

    if "Qwen" in args.model_name:
        tokenizer.padding_side = "left"
        tokenizer.pad_token = tokenizer.eos_token if tokenizer.pad_token is None else tokenizer.pad_token
    llm.set_tokenizer(tokenizer)

    formatted_messages = [
        f"You are a helpful assistant.\nUser: {sample}\nAssistant:" for sample in sample_list
    ]

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=1024,
        repetition_penalty=1.0,
        top_p=0.9,
        top_k=50,
        best_of=1
    )
    results = []
    for i in tqdm(range(0, len(sample_list), batch_size), desc="Processing", unit="batch"):
        batch = formatted_messages[i:i + batch_size]
        outputs = llm.generate(batch, sampling_params)
        batch_results = [output.outputs[0].text.strip() for output in outputs]
        results.extend(batch_results)

    assert len(results) == len(sample_list)
    return results


def prepare_eval_data(data_path):
    """
    Prepare evaluation data from JSONL file.
    
    Args:
        data_path: Path to the JSONL data file
        
    Returns:
        tuple: (sample_list, gt_list) where:
            sample_list: List of questions
            gt_list: List of ground truth answers
    """
    data = read_jsonl(data_path)
    all_sample_list = [
        item['question'] for item in data
    ]
    all_gt_list = [item['ground truth'] for item in data]
    return all_sample_list, all_gt_list


def prepare_sft_train_data():
    """
    Prepare data for supervised fine-tuning.
    
    Returns:
        Dataset: HuggingFace Dataset object containing formatted training examples
        
    Formats each example as:
    {
        "input_text": question,
        "target_text": prediction_budget
    }
    """
    data = read_jsonl(args.train_data_path)
    cleaned_data = [{
        "question": item['question'],
        "prediction": item['prediction_budget']  
    } for item in data]

    def format_example(example):
        return {"input_text": f"{example['question']}",
                "target_text": f"{example['prediction']}"}

    train_dataset = Dataset.from_list([format_example(d) for d in cleaned_data])
    return train_dataset


def prepare_dpo_train_data():
    """
    Prepare data for Direct Preference Optimization (DPO) training.
    
    Returns:
        Dataset: HuggingFace Dataset object containing formatted training examples
        
    Formats each example as:
    {
        "prompt": input prompt,
        "chosen": preferred response,
        "rejected": non-preferred response
    }
    """
    data = read_jsonl(args.data_path)
    cleaned_data = [{
        "prompt": item['prompt'],
        "chosen": item['chosen'],
        "rejected": item['rejected']
    } for item in data]

    def format_example(example):
        return {"prompt": f"{example['prompt']}",
                "chosen": f"{example['chosen']}",
                "rejected": f"{example['rejected']}"}

    train_dataset = Dataset.from_list([format_example(d) for d in cleaned_data])
    return train_dataset


def evaluate():
    """
    Evaluate model performance on test data.
    Returns:
        list: List of evaluation metrics
    """
    def AvgLength(sample_list, gt_list):
        logger.info(f"Data size: {len(sample_list)}")
        args.model = args.model_name
        logger.info(f"Evaluation for {args.strategy}!")
        pred_list = inference_eval(
            sample_list, args.model_path, args.lora_path, args.batch_size
        )
        # dump to results
        assert len(sample_list) == len(gt_list) == len(pred_list)
        acc_num = 0
        total_length = 0
        results = []
        start_time = time.time()
        for i in range(len(pred_list)):
            results.append({
                "ground truth": gt_list[i],
                "question": sample_list[i],
                "prediction": pred_list[i],
            })
            total_length += token_measure(pred_list[i])
            if evaluator.evaluate_sample(results[-1], cloze=True):
                acc_num += 1
        logger.info("=" * 30 + 'Evaluation Results' + "=" * 30 + '\n')
        logger.info(f'Accuracy: {100 * (acc_num / len(results)):.2f}%')
        logger.info(f"Token costs: {total_length / acc_num:.2f}")
        logger.info(f'Time cost: {time.time() - start_time}')
        return results

    evaluator = AccEvaluator()
    all_sample_list, all_gt_list = prepare_eval_data(args.test_data_path)
    val_res = AvgLength(all_sample_list, all_gt_list)
    logger.info("=" * 30 + 'END' + "=" * 30 + '\n')
    logger.info(f"Saved to " + os.path.join(args.output_dir, f'internalize-{args.strategy}.jsonl'))
    save_to_jsonl(val_res, os.path.join(args.output_dir, f'internalize-{args.strategy}.jsonl'))


def tokenize_data(dataset, tokenizer):
    """
    Tokenize dataset for training.
    
    Args:
        dataset: HuggingFace Dataset to tokenize
        tokenizer: Tokenizer to use
        
    Returns:
        Dataset: Tokenized dataset with input_ids and labels
    """
    def tokenize_function(examples):
        input_texts = examples["input_text"]
        output_texts = examples["target_text"]
        full_texts = [inp + "\n" + out for inp, out in zip(input_texts, output_texts)]
        tokenized = tokenizer(full_texts, padding="max_length", truncation=True, max_length=2048)
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    return tokenized_dataset


def load_model(model_path, lora_path=None):
    """
    Load and prepare model for training or inference.
    
    Args:
        model_path: Path to base model
        lora_path: Optional path to LoRA weights
        
    Returns:
        tuple: (model, tokenizer) where:
            model: Loaded and prepared model
            tokenizer: Configured tokenizer
    """
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    if args.model_name in ['Qwen2.5-14B', 'Qwen2.5-7B-Instruct-1M']:
        tokenizer.padding_side = "left"
        tokenizer.pad_token = tokenizer.eos_token if tokenizer.pad_token is None else tokenizer.pad_token
    base_model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True)
    base_model.eval()
    logger.info(f"Load base model from {model_path}")
    logger.info(f"Tokenizer max length: {tokenizer.model_max_length}")
    logger.info(f"Model config max length: {base_model.config.max_position_embeddings}")

    if lora_path is None:
        return base_model, tokenizer
    lora_model = PeftModel.from_pretrained(base_model, lora_path)
    logger.info(f"Load LoRA model from {lora_path} Successfully!")
    merged_model = lora_model.merge_and_unload()
    assert not isinstance(merged_model, PeftModel), "merge_and_unload failed"
    merged_model.half()
    merged_model.eval()
    return merged_model, tokenizer


def train_model_with_lora(model, tokenizer, dataset):
    """
    Train model using LoRA fine-tuning.
    
    Args:
        model: Base model to fine-tune
        tokenizer: Tokenizer for data processing
        dataset: Training dataset
    """
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"]
    )
    model = get_peft_model(model, lora_config)

    tokenized_dataset = tokenize_data(dataset, tokenizer)
    os.makedirs(os.path.join(args.output_dir, 'logs'), exist_ok=True)
    training_args = TrainingArguments(
        log_level="info",
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=8,
        num_train_epochs=args.epoch,
        save_steps=1,
        save_strategy="steps",
        save_total_limit=100,
        eval_strategy="no",
        logging_dir=os.path.join(args.output_dir, 'logs'),
        logging_steps=1,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        fp16=True
    )
    with open(os.path.join(args.output_dir, 'logs', 'train-args.jsonl'), "w") as f:
        json_line = json.dumps(training_args.to_dict())
        f.write(json_line + "\n")
    log_file = os.path.join(args.output_dir, 'logs', 'log.jsonl')
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        callbacks=[LoggingCallback(log_file)],
        processing_class=tokenizer,
    )
    logger.info("Lora initialized!")
    trainer.train()
    save_to_jsonl(trainer.state.log_history, log_file)
    if args.save:
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)


def train_model_with_dpo(model, tokenizer, dataset):
    """
    Train model using Direct Preference Optimization (DPO).
    
    Args:
        model: Base model to fine-tune
        tokenizer: Tokenizer for data processing
        dataset: Training dataset
    """
    os.makedirs(os.path.join(args.output_dir, 'logs'), exist_ok=True)
    logger.info(f"Saving to {args.output_dir}")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"]
    )
    model = get_peft_model(model, lora_config)

    training_args = DPOConfig(
        output_dir=args.output_dir,
        log_level="info",
        logging_dir=os.path.join(args.output_dir, 'logs'),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=16,
        num_train_epochs=args.epoch,
        learning_rate=args.learning_rate,
        logging_steps=1,
        save_strategy="steps",
        save_steps=1,
        report_to="none",
        fp16=False,
        save_total_limit=200,
        weight_decay=0.001,
        max_length=args.max_new_token,
        seed=SEED,
        data_seed=SEED,
        logging_first_step=True,
        beta=0.5,
        max_grad_norm=5.0
    )

    trainer = DPOTrainer(
        model=model,
        args=training_args,
        processing_class=tokenizer,
        ref_model=None,
        train_dataset=dataset,
        eval_dataset=None,
    )
    trainer.train()
    logger.info(trainer.state.log_history)
    save_to_jsonl(trainer.state.log_history, os.path.join(args.output_dir, 'logs', 'log.jsonl'))
    if args.save:
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)


def main():
    args.model_path = os.path.join('.cache', args.model_name)
    if args.eval:
        args.output_dir = os.path.join(args.output_dir, "Inference")
        os.makedirs(args.output_dir, exist_ok=True)
        evaluate()
    elif args.strategy == "lora":
        args.output_dir = os.path.join(args.output_dir, args.model_name, "LoRA")
        if args.save:
            logger.info(f"Saving to {args.output_dir}")
        dataset = prepare_sft_train_data()
        logger.info("Data Prepared Successfully!")
        model, tokenizer = load_model(args.model_path, args.lora_path)
        logger.info("Model Loaded Successfully!")
        train_model_with_lora(model, tokenizer, dataset)
    elif args.strategy == "dpo":
        args.output_dir = os.path.join(args.output_dir, args.model_name, "DPO")
        dataset = prepare_dpo_train_data()
        logger.info("Data Prepared Successfully!")
        tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(args.model_path, local_files_only=True)
        train_model_with_dpo(model, tokenizer, dataset)


if __name__ == "__main__":
    args = parse_args()
    main()
