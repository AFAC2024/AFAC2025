"""
GSM8K Zero-shot dataset module for loading and processing GSM8K math problems.
"""

import os
from torch.utils.data import Dataset
import logging
from utils import *

logger = logging.getLogger(__name__)


class GSM8KZero(Dataset):
    """
    Dataset class for GSM8K zero-shot learning.
    """
    
    def __init__(self, args, with_reasoning=True, name=None, cache=True, budget=None):
        """
        Initialize the GSM8K Zero-shot dataset.
        
        Args:
            args: Command line arguments containing configuration
            with_reasoning (bool): Whether to include step-by-step reasoning
            name (str, optional): Name of the dataset variant
            cache (bool): Whether to cache the processed data
            budget (int, optional): Token budget for prompt generation
        """
        self.args = args
        self.cache = cache
        self.with_reasoning = with_reasoning
        if budget is not None:
            global gsm8k_prompts
            gsm8k_prompts = create_gsm8k_prompt(budget)

        self.gsm8k_std_data_sets = self._load_data()
        logger.info("Loading dataset from the GSM8k-Zero!")
        self.dataset = sum(self.gsm8k_std_data_sets.values(), [])

    def _generate_configs(self):
        """
        Generate configuration for dataset loading.
        
        Returns:
            list: List of configuration dictionaries containing:
                - abbr: Dataset abbreviation
                - path: Path to dataset files
                - name: Dataset name
                - reader_cfg: Input/output column configuration
                - meta_prompt: Prompt template configuration
        """
        config = [{
            'abbr': 'GSM8K',
            'path': './data/GSM8K-Zero',
            'name': 'GSM8K-Zero',
            'reader_cfg': {
                'input_column': 'question',
                'output_column': 'answer'
            },
            'meta_prompt': {
                'round': gsm8k_prompts['reasoning'] if self.with_reasoning else gsm8k_prompts['no_reasoning']
            }
        }]
        save_config(config[0])
        return config

    @staticmethod
    def _generate_std_subset(raw_data, cfg):
        """
        Generate standardized subset of the dataset.
        
        Args:
            raw_data: Raw data from the dataset
            cfg: Configuration dictionary
            
        Returns:
            list: List of processed examples, each containing:
                - gold: Ground truth answer
                - round: List of conversation turns with human and bot messages
        """
        examples = []
        prompt_template = cfg["meta_prompt"]["round"][0]['prompt']
        for item in raw_data:
            examples.append({
                'gold': item['answer'],
                'round': [
                    {
                        "role": "HUMAN",
                        "prompt": prompt_template.replace("{question}", item['question'])
                    },
                    {
                        "role": "BOT",
                        "prompt": "{answer}"
                    }
                ]
            })
        return examples

    @staticmethod
    def _generate_formal_info(cfg):
        """
        Generate formalized information from raw data files.
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            list: List of processed data items, each containing:
                - question: The math problem
                - answer: The numerical answer as a string
        """
        data = []
        filename = f"{os.path.join(cfg['path'], cfg['name'])}.jsonl"
        with open(filename, 'r', encoding='utf-8') as infile:
            for ids, line in enumerate(infile):
                entry = json.loads(line)
                data.append({
                    'question': entry['question'].strip(),
                    'answer': str(int(entry['answer'])).strip()
                })
        return data

    def _load_data(self):
        """
        Load and process the dataset.
        
        Returns:
            dict: Dictionary mapping dataset abbreviations to processed subsets
        """
        cfgs = self._generate_configs()
        save_config(cfgs[0])
        std_data_sets = {}
        for cfg in cfgs:
            info = self._generate_formal_info(cfg)
            std_subset = self._generate_std_subset(info, cfg)
            save_to_jsonl(std_subset, os.path.join('./.cache', cfg["abbr"]) + '.jsonl')
            std_data_sets[cfg["abbr"]] = std_subset
        return std_data_sets

    def __len__(self):
        """
        Get the total number of examples in the dataset.
        
        Returns:
            int: Number of examples
        """
        return len(self.dataset)

    def __getitem__(self, i):
        """
        Get a specific example from the dataset.
        
        Args:
            i: Index of the example to retrieve
            
        Returns:
            dict: The example at index i
        """
        return self.dataset[i]



