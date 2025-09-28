"""
AFAC dataset module for loading and processing AFAC data.
"""

import os
import re
from torch.utils.data import Dataset
import logging
from utils import *

class AFACDataset(Dataset):
    """
    Dataset class for AFAC data.
    """

    def __init__(self, args, with_reasoning=True, cache=True, name=None, budget=None, split='train'):
        """
        Initialize the AFAC dataset.

        Args:
            args: Command line arguments containing configuration
            with_reasoning (bool): Whether to include step-by-step reasoning
            cache (bool): Whether to cache the processed data
            name (str, optional): Name of the dataset variant
            budget (int, optional): Token budget for prompt generation
            split (str): Dataset split ('train' or 'test')
        """
        self.args = args
        self.cache = cache
        self.split = split
        self.with_reasoning = with_reasoning
        self.dataset = self._load_data()
        logger.info(f"Loading dataset from the AFAC-{split}!")

    def _load_data(self):
        """
        Load and process the dataset.

        Returns:
            list: List of processed data samples
        """
        data_path = os.path.join(self.args.data_dir, f"afac_{self.split}.jsonl")
        data = read_jsonl(data_path)
        # Parse \boxed{} format in answers
        for sample in data:
            if 'answer' in sample:
                boxed_pattern = re.compile(r'\\boxed\{(.*?)\}', re.IGNORECASE)
                match = boxed_pattern.search(sample['answer'])
                if match:
                    sample['answer'] = match.group(1)
        return data

    def __len__(self):
        """
        Get the total number of examples in the dataset.

        Returns:
            int: Number of examples
        """
        return len(self.dataset)

    def __getitem__(self, idx):
        """
        Get a specific example from the dataset.

        Args:
            idx: Index of the example to retrieve

        Returns:
            dict: The example at index idx
        """
        return self.dataset[idx]