"""
MathBench dataset module for loading and processing mathematical benchmark data.
"""

import os
from torch.utils.data import Dataset
import logging
from utils import *

logger = logging.getLogger(__name__)


class MathBenchDataset(Dataset):
    """
    Dataset class for mathematical benchmark problems.
    """
    
    def __init__(self, args, with_reasoning=True, name=None, cache=True, budget=None):
        """
        Initialize the MathBench dataset.
        
        Args:
            args: Command line arguments containing configuration
            with_reasoning (bool): Whether to include step-by-step reasoning
            name (str, optional): Name of specific dataset subset to load
            cache (bool): Whether to cache the processed data
            budget (int, optional): Token budget for prompt generation
        """
        self.args = args
        self.cache = cache
        self.with_reasoning = with_reasoning
        if budget is not None:
            global single_choice_prompts, cloze_prompts
            cloze_prompts = create_cloze_prompt(budget)
            single_choice_prompts = create_prompt(budget)

        self.mathbench_std_data_sets = self._load_data()
        if name is None:
            logger.info("Loading all subsets from the mathbenchmark!")
            self.dataset = sum(self.mathbench_std_data_sets.values(), [])
        else:
            logger.info(f'Loading {name}')
            self.dataset = self.mathbench_std_data_sets[name]

    def _generate_configs(self):
        """
        Generate configuration for dataset loading.
        
        Returns:
            list: List of configuration dictionaries for each dataset subset, containing:
                - abbr: Dataset abbreviation
                - path: Path to dataset files
                - name: Dataset name
                - reader_cfg: Input/output column configuration
                - meta_prompt: Prompt template configuration (single-choice or cloze)
        """
        mathbench_cfgs = []
        for _split in list(mathbench_sets.keys()):
            for _name in mathbench_sets[_split]:
                mathbench_cfgs.append({
                    'abbr': 'mathbench-' + _split + '-' + _name,
                    'path': f'./data/mathbench_v1/{_split}',
                    'name': _name,
                    'reader_cfg': {
                        'input_column': 'question',
                        'output_column': 'answer'
                    },
                    'meta_prompt': {
                        'round': [
                            {
                                'role': 'HUMAN',
                                'prompt': single_choice_prompts[_name + '_with_reasoning'] if self.with_reasoning else
                                single_choice_prompts[_name]
                            },
                            {'role': 'BOT', 'prompt': '{answer}'}
                        ] if 'choice' in _name else (
                            cloze_prompts[_name + '_with_reasoning'] if self.with_reasoning else cloze_prompts[_name]
                        )
                    }
                })

        save_config(mathbench_cfgs[0])
        return mathbench_cfgs

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
                - question: The math problem (with options for single-choice)
                - answer: The answer as a string
        """
        data = []
        filename = f"{os.path.join(cfg['path'], cfg['name'])}.jsonl"
        with open(filename, 'r', encoding='utf-8') as infile:
            for id, line in enumerate(infile):
                entry = json.loads(line)
                if 'cloze' in cfg['name']:
                    data.append({
                        'question': entry['question'].strip(),
                        'answer': entry['answer'].strip()
                    })
                else:
                    question = entry['question'].strip() + '\n' + get_number(entry['options'])
                    info = {
                        'question': question,
                        'answer': entry['answer'].strip()
                    }
                    data.append(info)
        return data

    def _load_data(self):
        """
        Load and process the dataset.
        
        Returns:
            dict: Dictionary mapping dataset abbreviations to processed subsets
        """
        mathbench_cfgs = self._generate_configs()
        save_config(mathbench_cfgs[0])

        mathbench_std_data_sets = {}
        if os.path.exists('./.cache') and self.cache:
            for cfg in mathbench_cfgs:
                std_subset = read_jsonl(os.path.join('./.cache', cfg["abbr"]) + '.jsonl')
                mathbench_std_data_sets[cfg["abbr"]] = std_subset
        else:
            if not os.path.exists('./.cache'):
                os.mkdir('./.cache')
            for cfg in mathbench_cfgs:
                info = self._generate_formal_info(cfg)
                std_subset = self._generate_std_subset(info, cfg)
                save_to_jsonl(std_subset, os.path.join('./.cache', cfg["abbr"]) + '.jsonl')
                mathbench_std_data_sets[cfg["abbr"]] = std_subset
        return mathbench_std_data_sets

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

