#!/usr/bin/env python3
"""
Check AFAC dataset support and calculate optimal token budgets for each question.
This script verifies the AFAC dataset format and provides token budget analysis.
"""

import os
import json
import argparse
from utils import read_jsonl, token_measure, save_to_jsonl
from llm_datasets import AFACDataset
import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Args:
    """Simple args class for dataset initialization."""
    def __init__(self, data_dir='./data'):
        self.data_dir = data_dir


def check_afac_dataset():
    """Check if AFAC dataset is properly formatted and accessible."""
    logger.info("Checking AFAC dataset support...")
    
    # Check if data file exists
    data_path = './data/afac/afac.jsonl'
    if not os.path.exists(data_path):
        logger.error(f"AFAC dataset not found at {data_path}")
        return False
    
    # Load and validate data
    try:
        data = read_jsonl(data_path)
        logger.info(f"Successfully loaded {len(data)} questions from AFAC dataset")
        
        # Check data format
        if len(data) > 0:
            sample = data[0]
            required_keys = ['question', 'answer']
            for key in required_keys:
                if key not in sample:
                    logger.error(f"Missing required key '{key}' in dataset")
                    return False
            
            logger.info("Dataset format validation passed")
            return True
            
    except Exception as e:
        logger.error(f"Error loading AFAC dataset: {e}")
        return False
    
    return True


def analyze_question_complexity(question):
    """Analyze question complexity to estimate initial token budget."""
    # Simple heuristics for token budget estimation
    question_length = len(question)
    option_count = question.count('\n') - 1  # Count options (A, B, C, D...)
    
    # Base budget calculation
    base_budget = max(50, question_length // 2)
    
    # Adjust for complexity factors
    complexity_factors = {
        'multiple_choice': 1.2 if option_count > 0 else 1.0,
        'long_question': 1.5 if question_length > 200 else 1.0,
        'economic_terms': 1.3 if any(term in question.lower() for term in ['gdp', 'inflation', 'monetary', 'fiscal']) else 1.0
    }
    
    estimated_budget = int(base_budget * complexity_factors['multiple_choice'] * 
                          complexity_factors['long_question'] * complexity_factors['economic_terms'])
    
    return estimated_budget


def calculate_optimal_budgets():
    """Calculate optimal token budgets for each AFAC question."""
    logger.info("Calculating optimal token budgets for AFAC questions...")
    
    # Initialize dataset
    args = Args()
    try:
        dataset = AFACDataset(args, split='train')
        logger.info(f"AFAC dataset loaded successfully with {len(dataset)} questions")
    except Exception as e:
        logger.error(f"Error initializing AFAC dataset: {e}")
        return []
    
    # Analyze each question
    budget_analysis = []
    
    for idx, instance in enumerate(dataset):
        question = instance['question']
        answer = instance['answer']
        
        # Calculate initial budget estimate
        estimated_budget = analyze_question_complexity(question)
        
        # Calculate actual token usage for answer
        actual_tokens = token_measure(answer)
        
        # Store analysis
        analysis = {
            'question_id': idx,
            'question': question,
            'answer': answer,
            'estimated_budget': estimated_budget,
            'actual_answer_tokens': actual_tokens,
            'recommended_budget': max(estimated_budget, actual_tokens * 3)  # Conservative estimate
        }
        
        budget_analysis.append(analysis)
        
        if idx < 5:  # Log first few examples
            logger.info(f"Question {idx}: estimated={estimated_budget}, actual={actual_tokens}, recommended={analysis['recommended_budget']}")
    
    return budget_analysis


def generate_budget_report(budget_analysis):
    """Generate a comprehensive budget report."""
    if not budget_analysis:
        logger.error("No budget analysis data available")
        return
    
    # Calculate statistics
    total_questions = len(budget_analysis)
    avg_estimated = sum(item['estimated_budget'] for item in budget_analysis) / total_questions
    avg_actual = sum(item['actual_answer_tokens'] for item in budget_analysis) / total_questions
    avg_recommended = sum(item['recommended_budget'] for item in budget_analysis) / total_questions
    
    # Find min and max budgets
    min_budget = min(item['recommended_budget'] for item in budget_analysis)
    max_budget = max(item['recommended_budget'] for item in budget_analysis)
    
    logger.info("=" * 50)
    logger.info("AFAC Token Budget Analysis Report")
    logger.info("=" * 50)
    logger.info(f"Total questions analyzed: {total_questions}")
    logger.info(f"Average estimated budget: {avg_estimated:.1f} tokens")
    logger.info(f"Average actual answer tokens: {avg_actual:.1f} tokens")
    logger.info(f"Average recommended budget: {avg_recommended:.1f} tokens")
    logger.info(f"Budget range: {min_budget} - {max_budget} tokens")
    
    # Save detailed analysis
    output_path = './tmp/afac_budget_analysis.jsonl'
    os.makedirs('./tmp', exist_ok=True)
    save_to_jsonl(budget_analysis, output_path)
    logger.info(f"Detailed budget analysis saved to {output_path}")
    
    # Save summary
    summary = {
        'total_questions': total_questions,
        'average_estimated_budget': avg_estimated,
        'average_actual_tokens': avg_actual,
        'average_recommended_budget': avg_recommended,
        'min_budget': min_budget,
        'max_budget': max_budget,
        'budget_distribution': {
            'low': len([item for item in budget_analysis if item['recommended_budget'] < 100]),
            'medium': len([item for item in budget_analysis if 100 <= item['recommended_budget'] < 200]),
            'high': len([item for item in budget_analysis if item['recommended_budget'] >= 200])
        }
    }
    
    summary_path = './tmp/afac_budget_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"Budget summary saved to {summary_path}")


def main():
    """Main function to check AFAC support and calculate budgets."""
    logger.info("Starting AFAC dataset analysis...")
    
    # Check dataset support
    if not check_afac_dataset():
        logger.error("AFAC dataset check failed")
        return
    
    # Calculate optimal budgets
    budget_analysis = calculate_optimal_budgets()
    
    # Generate report
    generate_budget_report(budget_analysis)
    
    logger.info("AFAC dataset analysis completed successfully!")


if __name__ == "__main__":
    main()