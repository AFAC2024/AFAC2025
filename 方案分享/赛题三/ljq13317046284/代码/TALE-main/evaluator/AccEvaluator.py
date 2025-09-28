import logging
import re
from math_verify import parse, verify

logger = logging.getLogger(__name__)


class AccEvaluator:
    """
    A class for evaluating the accuracy of predictions against ground truth in various formats.
    """

    def __init__(self, dataset=None):
        """
        Initialize the AccEvaluator with an optional dataset.
        
        Args:
            dataset: Optional dataset to evaluate. If None, must be set later.
        """
        self.dataset = dataset

    def accuracy(self):
        """
        Calculate the overall accuracy across the entire dataset.
        
        Returns:
            float: The accuracy score as a ratio of correct predictions to total samples
        """
        acc_num = 0
        for sample in self.dataset:
            acc_num += self.evaluate_sample(sample)
        return acc_num / len(self.dataset)

    @staticmethod
    def find_answer(text):
        """
        Extract multiple choice answer (A, B, C, or D) from text response.
        
        Args:
            text: The text response to analyze
            
        Returns:
            str: The extracted answer choice (A, B, C, D) or 'None' if not found

        """
        text = text.strip()
        # Check for \boxed{} format
        boxed_pattern = re.compile(r'\\boxed\{([A-D])\}', re.IGNORECASE)
        boxed_match = boxed_pattern.search(text)
        if boxed_match:
            return boxed_match.group(1).upper()

        last_newline_index = text.rfind('\n')
        prediction = text[last_newline_index + 1:]
        if len(prediction) < 5:
            search_texts = [
                'the correct answer is',
                '答案为选项'
            ]
            for search_text in search_texts:
                index = text.find(search_text)
                if index != -1:
                    prediction = text[index:]
                    break

        pattern = re.compile(r'[ABCD]')
        matches = pattern.findall(prediction)
        if matches:
            answer = ''.join(matches)[-1]
        else:
            answer = 'None'

        return answer

    @staticmethod
    def extract_predicted_answer(text):
        """
        Extract numerical or text answer from a response.
        
        Args:
            text: The text response to analyze
            
        Returns:
            str or None: The extracted answer or None if no valid answer found

        """
        # Check for \boxed{} format
        boxed_pattern = re.compile(r'\\boxed\{(.*?)\}', re.IGNORECASE)
        boxed_match = boxed_pattern.search(text)
        if boxed_match:
            return boxed_match.group(1)

        pattern = r"\[\[(.*?)\]\]"
        match = re.findall(pattern, text)
        if match:
            return match[-1]

        regex_pattern = "(-?[$0-9.,]{2,})|(-?[0-9]+)"
        regexes_to_ignore = [
            ",",
            "\\$",
            "(?s).*#### ",
            "\\.$"
        ]
        match = re.findall(regex_pattern, text)
        if match:
            match = match[-1]
            if isinstance(match, tuple):
                match = [m for m in match if m][0]
            text = match.strip()
            for regex in regexes_to_ignore:
                text = re.sub(regex, "", text)
            return text
        else:
            return None

    def evaluate_sample(self, sample, cloze=True):
        """
        Evaluate a single sample against its ground truth.
        
        Args:
            sample: Dictionary containing 'ground truth' and 'prediction' keys
            cloze: Boolean indicating if this is a cloze-style question (True) or 
                  multiple choice (False)
            
        Returns:
            bool: True if the prediction matches ground truth, False otherwise
            
        """
        gt = sample['ground truth']
        pred = sample['prediction']
        if cloze:
            return (gt == self.extract_predicted_answer(pred)) or (f"[[{gt}]]" in pred) \
                   or verify(parse(gt), parse(self.extract_predicted_answer(pred)))
        else:
            if f'[[{gt}]]' in pred:
                return True
            choice = self.find_answer(sample['prediction'])
            return choice == gt
