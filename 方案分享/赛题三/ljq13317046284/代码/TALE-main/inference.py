import os
import argparse
from utils import *
from llm_datasets import GSM8KZero, GSM8K, GPQA, MathBenchDataset, AFACDataset
from llm_models import LLMModel
import time
import logging
from evaluator import AccEvaluator

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_data(args):
    """
    Prepare the dataset based on the data_name argument.

    Args:
        args: Command line arguments

    Returns:
        Dataset: Loaded dataset
    """
    if args.data_name == 'GSM8K-Zero':
        dataset = GSM8KZero(args, with_reasoning=args.reasoning, cache=False)
    elif args.data_name == 'GSM8K':
        dataset = GSM8K(args, with_reasoning=args.reasoning, cache=False)
    elif 'math' in args.data_name:
        dataset = MathBenchDataset(args, with_reasoning=args.reasoning, cache=False)
    elif args.data_name == 'afac':
        dataset = AFACDataset(args, with_reasoning=args.reasoning, cache=False)
    else:
        raise ValueError(f"Dataset {args.data_name} not supported.")
    return dataset


def data2list(dataset):
    """
    Convert dataset instances to lists of samples and ground truths.
    
    Args:
        dataset: The dataset to convert
        
    Returns:
        tuple: (sample_list, gt_list) where:
            sample_list: List of prompt strings
            gt_list: List of ground truth answers
    """
    sample_list = []
    gt_list = []
    for idx, instance in enumerate(dataset):
        cur_sample = instance['round']
        ground_truth = instance['gold']
        sample_list.append(cur_sample[0]['prompt'])
        gt_list.append(ground_truth)
    return sample_list, gt_list


def inference_local(args, dataset, model, evaluator):
    """
    Run inference using a local model (e.g. Hugging Face models).
    
    Args:
        args: Command line arguments
        dataset: Dataset to run inference on
        model: The local LLM model instance
        evaluator: AccEvaluator instance for accuracy calculation
        
    Results include accuracy percentage and average token cost per sample.
    """
    acc_num = 0
    token_num = 0
    results = []
    start_time = time.time()
    logger.info("=" * 30 + 'Requesting' + "=" * 30 + '\n')
    # process data in list
    logger.info(f"data size: {len(dataset)}")
    sample_list, gt_list = data2list(dataset)
    sample_list, gt_list = sample_list[args.start_index:args.end_index], gt_list[args.start_index:args.end_index]
    pred_list = model.query_batch(sample_list)
    # dump to results
    assert len(sample_list) == len(gt_list) == len(pred_list)
    for i in range(len(pred_list)):
        results.append({
            "ground truth": gt_list[i],
            "question": sample_list[i],
            "prediction": pred_list[i],
        })
        acc_num += evaluator.evaluate_sample(results[-1],
                                             cloze=('cloze' in args.data_name) or (
                                                     args.data_name in ['GSM8K', 'GSM8K-Zero']))
        token_num += token_measure(pred_list[i])
    logger.info(f'Accuracy: {100 * acc_num / len(results):.2f}%')
    logger.info(f'Token costs: {token_num / len(results):.2f}')
    save_to_jsonl(results, args.output_path)
    logger.info(f'Time cost: {time.time() - start_time}')


def inference_api(args, dataset, model, evaluator, key):
    """
    Run inference using an API-based model (e.g. GPT-4, Claude).
    
    Args:
        args: Command line arguments
        dataset: Dataset to run inference on
        model: The API-based LLM model instance
        evaluator: AccEvaluator instance for accuracy calculation
        key: API key for model access
    """
    acc_num = 0
    results = []
    start_time = time.time()
    logger.info("=" * 30 + 'Requesting' + "=" * 30 + '\n')
    if args.end_index is None:
        args.end_index = len(dataset)
    for idx, instance in enumerate(dataset):
        # logger.info(idx)
        if args.start_index <= idx < args.end_index:
            cur_sample = instance['round']
            ground_truth = instance['gold']
            logger.info('=' * 30 + f"Step: {idx + 1} / {args.end_index}" + '=' * 30)
            # pred = model.query(cur_sample, key=keys[args.key_index])
            logger.info(f"Question: {cur_sample[0]['prompt']}")
            pred = model.query(cur_sample, key=key)
            results.append({
                "ground truth": ground_truth,
                "question": cur_sample[0]['prompt'],
                "prediction": pred[0][0],
            })
            acc_num += evaluator.evaluate_sample(results[-1],
                                                 cloze=('cloze' in args.data_name) or (
                                                         args.data_name in ['GSM8K', 'GSM8K-Zero']))
            logger.info(f'Accuracy: {acc_num / len(results)}')
            # logger.info(f"Ground truth: {ground_truth}")
            # logger.info(f"Prediction: {pred[0][0]}")
            save_to_jsonl(results, args.output_path)
            logger.info(f'Time cost: {time.time() - start_time}')


def parse_args():
    """
    Parse command line arguments for the inference script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", default=64, type=int, help="=The budget token for our tech.")
    parser.add_argument("--budget", default=None, help="=The budget token for our tech.")
    parser.add_argument("--reasoning", action='store_true', help="If we use LLM reasoning.")
    parser.add_argument("--model", default='DeepSeek-R1-Distill-Qwen-1.5B', help="The model name on huggingface.")
    parser.add_argument("--output_path", default='./tmp',
                        help="The output path to save the model output.")
    parser.add_argument("--n", default=1, type=int, help="Number of samples from LLM.")
    parser.add_argument("--start_index", default=0, type=int, help="The start index for the dataset.")
    parser.add_argument("--end_index", default=None, type=int, help="The end index for the dataset.")
    parser.add_argument("--key_index", default=1, type=int, help="The key index for the dataset.")
    parser.add_argument("--data_name", default='GSM8K-Zero',
                        type=str, help="The dataset name used during our evaluation.")
    return parser.parse_args()


def main():
    # prepare keys and arguments
    args = parse_args()
    args.output_path = os.path.join(args.output_path, args.model, args.data_name)
    if not os.path.exists(args.output_path):
        os.makedirs(args.output_path)
    args.output_path = os.path.join(args.output_path,
                                    'output_with_reasoning.jsonl'
                                    if args.reasoning else 'output_without_reasoning_new_prompt.jsonl')
    logger.info(f'Saving to {args.output_path}')
    args.local = (args.model in ['Llama-3.1-8B-Instruct']) or 'Qwen' in args.model  
    keys = {
        'yi-lightning': ['your_api_key', 'your_api_key'],
        'gpt-4o-mini': ['your_api_key', 'your_api_key'],
        'gpt-4o-2024-05-13': ['your_api_key', 'your_api_key'],
        'deepseek-v3': ['your_deepseek_api_key_1', 'your_deepseek_api_key_2']
    }
    key = keys[args.model][args.key_index] if not args.local else None

    # Prepare dataset
    dataset = prepare_data(args)
    # dataset = Subset(dataset, list(range(1500, 2000)))

    # Prepare evaluator
    evaluator = AccEvaluator(dataset)

    # Prepare llm model
    model = LLMModel(args)
    if args.end_index is None:
        args.end_index = len(dataset)
    args.end_index = min(args.end_index, len(dataset))

    # inference
    if args.local:
        inference_local(args, dataset, model, evaluator)
    else:
        inference_api(args, dataset, model, evaluator, key)


if __name__ == "__main__":
    main()