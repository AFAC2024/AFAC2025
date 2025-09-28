#!/usr/bin/env python3
import os
import random
import argparse
from utils import *
from torch.utils.data import Subset
from llm_datasets import MathBenchDataset, GSM8K, GPQA, GSM8KZero
from llm_models import LLMModel
import time
import logging
from evaluator import AccEvaluator
from langchain.prompts import PromptTemplate

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    """
    Parse command line arguments for the TALE-EP script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--reasoning", action='store_true', help="If we use LLM reasoning.")
    parser.add_argument("--model", default='gpt-4o-mini', help="The model name on huggingface.")
    parser.add_argument("--output_path", default='./temp/100-test',
                        help="The output path to save the model output.")
    parser.add_argument("--n", default=1, type=int, help="Number of samples from LLM.")
    parser.add_argument("--start_index", default=0, type=int, help="The start index for the dataset.")
    parser.add_argument("--end_index", default=100, type=int, help="The end index for the dataset.")
    parser.add_argument("--key_index", default=2, type=int, help="The key index for the dataset.")
    parser.add_argument("--data_name", default='GSM8K',
                        type=str, help="The dataset name used during our evaluation.")
    return parser.parse_args()


def Adapter(dataset, model, key, args):
    """
    Adapts the dataset for evaluation using the specified model and parameters.
    
    Args:
        dataset: The input dataset to process
        model: The LLM model instance to use for queries
        key: API key for model access
        args: Command line arguments containing configuration parameters
    """
    evaluator = AccEvaluator()
    zero_shot_context = create_zero_shot_context()
    budget_pred_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "{context}\n\n"
            "Below is the question:\n\n"
            "Question: \"{question}\"\n"
        )
    )
    results, acc_num = [], 0.0
    logger.info("=" * 30 + 'Requesting' + "=" * 30 + '\n')
    if args.end_index is None:
        args.end_index = len(dataset)
    start_time = time.time()
    for index, data in enumerate(dataset):
        if args.start_index <= index < args.end_index:
            logger.info('=' * 30 + f"Step: {index + 1} / {args.end_index}" + '=' * 30)
            item = {
                'question': extract_question(dataset[index]['round'][0]['prompt']),
                'ground truth': dataset[index]['gold']
            }
            format_prompt = budget_pred_prompt.format(
                context=zero_shot_context,
                question=item['question']
            )
            answer, _, _ = model.query([{'prompt': format_prompt}], key=key)
            budget_pred = int(extract_number(answer[0]))
            new_question = add_budget(dataset[index]['round'][0]['prompt'], budget_pred)
            logger.info(new_question)
            new_answer, _, _ = model.query([{'prompt': new_question}], key=key)
            results.append(
                {
                    'question': new_question,
                    'ground truth': item['ground truth'],
                    'budget_TALE': budget_pred,
                    'token_cost': token_measure(new_answer[0]),
                    'prediction': new_answer[0],
                }
            )
            save_to_jsonl(results, args.output_path)
            acc_num += evaluator.evaluate_sample(results[-1],
                                                 cloze=('cloze' in args.data_name) or (args.data_name == 'GSM8K'))
            logger.info(f'Accuracy: {acc_num / len(results)}')
            logger.info(f'Time cost: {time.time() - start_time}')


def main():
    """
    Main entry point for the TALE-EP script.
    """
    args = parse_args()
    args.reasoning = True
    args.output_path = os.path.join(args.output_path, args.model, args.data_name)
    if not os.path.exists(args.output_path):
        os.makedirs(args.output_path)
    args.output_path = os.path.join(args.output_path, 'TALE.jsonl')
    logger.info(f'Saving to {args.output_path}')
    keys = {
        'yi-lightning': ['your_api_key', 'your_api_key'],
        'gpt-4o-mini': ['your_api_key', 'your_api_key'],
        'gpt-4o-2024-05-13': ['your_api_key', 'your_api_key'],
    }
    key = keys[args.model][args.key_index]
    # Prepare dataset
    if 'math' in args.data_name:
        if args.data_name == 'math':
            dataset = MathBenchDataset(args, with_reasoning=args.reasoning, cache=False)
        else:
            dataset = MathBenchDataset(args, with_reasoning=args.reasoning,
                                       name=args.data_name, cache=False)
    elif args.data_name == 'GSM8K':
        dataset = GSM8K(args, with_reasoning=args.reasoning,
                        name=args.data_name, cache=False)
    elif args.data_name == 'GSM8K-Zero':
        dataset = GSM8KZero(args, with_reasoning=args.reasoning,
                            name=args.data_name, cache=False)
    elif args.data_name == 'afac':
        dataset = read_jsonl(os.path.join('data', 'afac', 'afac.jsonl'))
        for item in dataset:
            item['gold'] = item['answer'].replace('\\boxed{', '').replace('}', '')
    else:
        dataset = None
        ValueError(f"{args.data_name} is not supported!")

    # Prepare llm model
    model = LLMModel(args)
    Adapter(dataset, model, key, args)


if __name__ == "__main__":
    main()
