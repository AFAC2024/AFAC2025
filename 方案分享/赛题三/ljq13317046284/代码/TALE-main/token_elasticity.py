#!/usr/bin/env python3
import os
import random
import argparse
from utils import *
from torch.utils.data import Subset
from llm_datasets import MathBenchDataset
from llm_models import LLMModel
import time
import pickle
import numpy as np
import logging
from evaluator import AccEvaluator

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    # filename='tmp/search_budget/gpt-4o-mini/log',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def search_budget(instance, budget, model, evaluator, key='your_api_key'):
    """
    Search for optimal token budget while tracking budget and token usage progression.
    
    Args:
        instance: Dictionary containing question and ground truth
        budget: Initial token budget (upper bound)
        model: LLM model instance
        evaluator: AccEvaluator instance for accuracy checking
        key: API key for model access (default: 'your_api_key')
        
    Returns:
        tuple: (updated_instance, final_budget, budget_list, token_list) where:
            updated_instance: Original instance with added budget information
            final_budget: The optimal budget found
            budget_list: List of all budget values tried during search
            token_list: List of actual token usage for each budget tried
    """
    pred_flag = evaluator.evaluate_sample(instance)
    upper_bound = budget
    pre_token_cost = upper_bound
    instance['question_budget'] = 'None'
    instance['prediction_budget'] = 'None'
    instance['budget'] = upper_bound
    budget_list = [upper_bound]
    token_list = [upper_bound]
    while pred_flag:
        new_question = add_budget(instance['question'], budget // 2)
        cur_sample = [{'prompt': new_question}]
        cur_answer = model.query(cur_sample, key=key)[0][0]
        cur_token_cost = token_measure(cur_answer)
        pred_flag = evaluator.evaluate_sample({
            'ground truth': instance['ground truth'],
            'prediction': cur_answer
        })
        if pred_flag and budget // 2 >= 1:
            # update current best answer and budge
            logger.info(f'Searching budget from {budget} to {budget // 2}.')
            logger.info(f'Token costs from {pre_token_cost} to {cur_token_cost}')
            instance['question_budget'] = new_question
            instance['prediction_budget'] = cur_answer
            instance['budget'] = budget // 2
            budget //= 2
            pre_token_cost = cur_token_cost
            budget_list.append(budget)
            token_list.append(cur_token_cost)
        else:
            break
    return instance, budget, budget_list, token_list


def main():
    """
    Main entry point for the token elasticity analysis script.
    
    This function:
    1. Parses command line arguments for configuration
    2. Sets up output paths and logging
    3. Loads dataset from raw data file
    4. Initializes model and evaluator
    5. For each valid instance:
       - Determines initial budget from original prediction
       - Searches for optimal budget while tracking elasticity
       - Saves progression of budget and token usage.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", default=None, help="=The budget token for our tech.")
    parser.add_argument("--do_search", action='store_true', help="If we search the best budget.")
    parser.add_argument("--model", default='yi-lightning', help="yi-lightning, gpt-4o-mini. gpt-4o")
    parser.add_argument("--output_path", default='./tmp/search_budget',
                        help="The output path to save the model output.")
    parser.add_argument("--n", default=1, type=int, help="Number of samples from LLM.")
    parser.add_argument("--start_index", default=0, type=int, help="The start index for the dataset.")
    parser.add_argument("--end_index", default=700, type=int, help="The end index for the dataset.")
    parser.add_argument("--key_index", default=0, type=int, help="The key index for the dataset.")
    parser.add_argument("--data_name", default=None,
                        type=str, help="The dataset name used during our evaluation.")
    args = parser.parse_args()
    args.output_path = os.path.join(args.output_path, args.model, 'search_budget.jsonl')
    logger.info(f'Saving to {args.output_path}')
    args.do_search = True
    dataset = read_jsonl(f'tmp/search_budget/gpt-4o-mini/raw_data.jsonl')
    model = LLMModel(args)
    keys = {
        'yi-lightning': ['your_api_key', 'your_api_key'],
        'gpt-4o-mini': ['your_api_key', 'your_api_key'],
        'gpt-4o-2024-05-13': ['your_api_key', 'your_api_key'],
    }
    key = keys[args.model][args.key_index]
    evaluator = AccEvaluator(dataset)
    res_budget = []
    res_token = []
    logger.info("=" * 30 + 'Requesting' + "=" * 30 + '\n')
    if args.end_index is None:
        args.end_index = len(dataset)
    for idx, instance in enumerate(dataset):
        if args.start_index <= idx < args.end_index:
            logger.info('=' * 30 + f"Step: {idx + 1} / {len(dataset)}" + '=' * 30)
            pred_flag = evaluator.evaluate_sample(instance)
            if not pred_flag:
                continue
            target_pred = instance['prediction']
            budget_upper_bound = token_measure(target_pred)
            logger.info(f'Step: {idx + 1}-{budget_upper_bound}')
            new_instance, budget, budget_list, token_list = search_budget(instance, budget_upper_bound,
                                                                          model, evaluator, key=key)
            logger.info("Updating Budget: {}/{}.".format(budget, budget_upper_bound))
            logger.info("Updating Token costs: {}/{}."
                        .format(token_measure(new_instance['prediction_budget']), budget_upper_bound))
            res_budget.append(budget_list)
            res_token.append(token_list)
            with open(f"tmp/search_budget/{args.model}/elasticity.pkl", "wb") as file:
                pickle.dump([res_budget, res_token], file)


if __name__ == "__main__":
    main()
