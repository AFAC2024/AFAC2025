"""
LLM Datasets package for loading and processing various mathematical and physics datasets.

This package provides dataset classes for:
1. GSM8K: Grade school math problems with step-by-step solutions
2. GSM8K Zero-shot: GSM8K problems for zero-shot learning scenarios
3. MathBench: Various mathematical benchmark datasets
4. GPQA: Graduate Physics Question Answering dataset
"""

from .math_bench import MathBenchDataset
from .gsm8k_zero import GSM8KZero
from .gsm8k import GSM8K
from .gpqa import GPQA
