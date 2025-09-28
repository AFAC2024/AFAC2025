#!/usr/bin/env python3
"""
Direct analysis of AFAC dataset without dataset class constraints.
This script directly reads afac.jsonl and provides comprehensive analysis.
"""

import os
import json
import re
from utils import read_jsonl, token_measure, save_to_jsonl
import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_afac_data():
    """Load AFAC data directly from jsonl file."""
    data_path = './data/afac/afac.jsonl'
    
    if not os.path.exists(data_path):
        logger.error(f"AFAC dataset not found at {data_path}")
        return None
    
    try:
        data = read_jsonl(data_path)
        logger.info(f"Successfully loaded {len(data)} questions from AFAC dataset")
        return data
    except Exception as e:
        logger.error(f"Error loading AFAC dataset: {e}")
        return None


def parse_answer(answer_text):
    """Parse boxed answer format."""
    if not answer_text:
        return ""
    
    # Handle boxed format
    boxed_pattern = re.compile(r'\\boxed\{(.*?)\}', re.IGNORECASE)
    match = boxed_pattern.search(answer_text)
    if match:
        return match.group(1)
    
    # Handle direct answer
    return answer_text.strip()


def analyze_question_complexity(question):
    """Analyze question complexity for token budget estimation."""
    if not question:
        return 50
    
    # Basic metrics
    char_count = len(question)
    word_count = len(question.split())
    line_count = question.count('\n')
    
    # Count options (A, B, C, D...)
    option_pattern = r'\n[A-D]\.'
    options = re.findall(option_pattern, question)
    option_count = len(options)
    
    # Complexity scoring
    complexity_score = 1.0
    
    # Length-based adjustment
    if char_count > 300:
        complexity_score *= 1.5
    elif char_count > 150:
        complexity_score *= 1.2
    
    # Option-based adjustment
    if option_count >= 4:
        complexity_score *= 1.3
    
    # Economic terms adjustment
    economic_terms = [
        'gdp', 'inflation', 'monetary', 'fiscal', 'unemployment', 'interest', 
        'exchange', 'trade', 'budget', 'tax', 'supply', 'demand', 'market',
        'currency', 'investment', 'consumption', 'production', 'elasticity'
    ]
    
    question_lower = question.lower()
    term_count = sum(1 for term in economic_terms if term in question_lower)
    if term_count > 2:
        complexity_score *= 1.4
    
    # Base calculation
    base_tokens = max(50, word_count * 2)
    estimated_budget = int(base_tokens * complexity_score)
    
    return estimated_budget


def calculate_token_statistics(data):
    """Calculate comprehensive token statistics."""
    stats = {
        'total_questions': len(data),
        'questions': []
    }
    
    total_question_chars = 0
    total_answer_chars = 0
    total_question_tokens = 0
    total_answer_tokens = 0
    
    for idx, item in enumerate(data):
        question = item.get('question', '')
        answer = parse_answer(item.get('answer', ''))
        
        # Token counts
        question_tokens = token_measure(question)
        answer_tokens = token_measure(answer)
        
        # Complexity analysis
        estimated_budget = analyze_question_complexity(question)
        
        # Store individual analysis
        question_analysis = {
            'id': idx,
            'question': question,
            'answer': answer,
            'question_chars': len(question),
            'answer_chars': len(answer),
            'question_tokens': question_tokens,
            'answer_tokens': answer_tokens,
            'estimated_budget': estimated_budget,
            'efficiency_ratio': answer_tokens / max(question_tokens, 1),
            'recommended_budget': max(estimated_budget, answer_tokens * 2, 100)
        }
        
        stats['questions'].append(question_analysis)
        
        # Accumulate totals
        total_question_chars += len(question)
        total_answer_chars += len(answer)
        total_question_tokens += question_tokens
        total_answer_tokens += answer_tokens
    
    # Calculate averages
    stats['avg_question_chars'] = total_question_chars / len(data)
    stats['avg_answer_chars'] = total_answer_chars / len(data)
    stats['avg_question_tokens'] = total_question_tokens / len(data)
    stats['avg_answer_tokens'] = total_answer_tokens / len(data)
    stats['avg_estimated_budget'] = sum(q['estimated_budget'] for q in stats['questions']) / len(data)
    stats['avg_recommended_budget'] = sum(q['recommended_budget'] for q in stats['questions']) / len(data)
    
    return stats


def generate_budget_recommendations(stats):
    """Generate budget recommendations based on analysis."""
    recommendations = {
        'dataset_info': {
            'name': 'AFAC Economics Dataset',
            'total_questions': stats['total_questions'],
            'format': 'Multiple choice economics questions'
        },
        'token_analysis': {
            'avg_question_tokens': round(stats['avg_question_tokens'], 1),
            'avg_answer_tokens': round(stats['avg_answer_tokens'], 1),
            'avg_recommended_budget': round(stats['avg_recommended_budget'], 1)
        },
        'budget_ranges': {
            'minimum': min(q['recommended_budget'] for q in stats['questions']),
            'maximum': max(q['recommended_budget'] for q in stats['questions']),
            'median': sorted(q['recommended_budget'] for q in stats['questions'])[len(stats['questions'])//2]
        },
        'distribution': {
            'low_budget': len([q for q in stats['questions'] if q['recommended_budget'] < 150]),
            'medium_budget': len([q for q in stats['questions'] if 150 <= q['recommended_budget'] < 300]),
            'high_budget': len([q for q in stats['questions'] if q['recommended_budget'] >= 300])
        },
        'optimization_tips': [
            'Use 2x answer token count as minimum budget',
            'Add 50-100 tokens for reasoning steps',
            'Increase budget for complex economic scenarios',
            'Consider question length and terminology complexity'
        ]
    }
    
    return recommendations


def save_analysis_results(stats, recommendations):
    """Save analysis results to files."""
    os.makedirs('./tmp', exist_ok=True)
    
    # Save detailed question analysis
    questions_file = './tmp/afac_questions_analysis.jsonl'
    save_to_jsonl(stats['questions'], questions_file)
    
    # Save summary statistics
    summary_file = './tmp/afac_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'statistics': stats,
            'recommendations': recommendations
        }, f, indent=2, ensure_ascii=False)
    
    # Save budget recommendations only
    budget_file = './tmp/afac_budget_recommendations.json'
    with open(budget_file, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Analysis saved to:")
    logger.info(f"  - Detailed questions: {questions_file}")
    logger.info(f"  - Summary statistics: {summary_file}")
    logger.info(f"  - Budget recommendations: {budget_file}")


def print_summary(stats, recommendations):
    """Print analysis summary to console."""
    print("\n" + "="*60)
    print("AFAC DATASET ANALYSIS SUMMARY")
    print("="*60)
    
    print(f"\nDataset Overview:")
    print(f"  Total Questions: {stats['total_questions']}")
    print(f"  Format: Multiple choice economics questions")
    
    print(f"\nToken Statistics:")
    print(f"  Average Question Tokens: {stats['avg_question_tokens']:.1f}")
    print(f"  Average Answer Tokens: {stats['avg_answer_tokens']:.1f}")
    print(f"  Average Recommended Budget: {stats['avg_recommended_budget']:.1f}")
    
    print(f"\nBudget Range:")
    print(f"  Minimum: {recommendations['budget_ranges']['minimum']} tokens")
    print(f"  Maximum: {recommendations['budget_ranges']['maximum']} tokens")
    print(f"  Median: {recommendations['budget_ranges']['median']} tokens")
    
    print(f"\nBudget Distribution:")
    print(f"  Low Budget (<150): {recommendations['distribution']['low_budget']} questions")
    print(f"  Medium Budget (150-300): {recommendations['distribution']['medium_budget']} questions")
    print(f"  High Budget (≥300): {recommendations['distribution']['high_budget']} questions")
    
    print("\nOptimization Tips:")
    for tip in recommendations['optimization_tips']:
        print(f"  - {tip}")
    
    print("="*60)


def main():
    """Main function to analyze AFAC dataset."""
    logger.info("Starting AFAC dataset analysis...")
    
    # Load data
    data = load_afac_data()
    if data is None:
        logger.error("Failed to load AFAC dataset")
        return
    
    # Calculate statistics
    logger.info("Analyzing question complexity and token requirements...")
    stats = calculate_token_statistics(data)
    
    # Generate recommendations
    recommendations = generate_budget_recommendations(stats)
    
    # Save results
    save_analysis_results(stats, recommendations)
    
    # Print summary
    print_summary(stats, recommendations)
    
    logger.info("AFAC dataset analysis completed successfully!")


if __name__ == "__main__":
    main()