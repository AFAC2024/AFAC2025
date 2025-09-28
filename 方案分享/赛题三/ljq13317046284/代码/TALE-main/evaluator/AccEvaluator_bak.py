import logging
import re

logger = logging.getLogger(__name__)


class AccEvaluator:
    def __init__(self, dataset=None):
        self.dataset = dataset

    def accuracy(self):
        acc_num = 0
        for sample in self.dataset:
            acc_num += self.evaluate_sample(sample)
        return acc_num / len(self.dataset)

    @staticmethod
    def find_answer(text):
        text = text.strip()
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
        gt = sample['ground truth']
        pred = sample['prediction']
        if cloze:
            return gt == self.extract_predicted_answer(pred)
        else:
            if f'[[{gt}]]' in pred:
                return True
            choice = self.find_answer(sample['prediction'])
            return choice == gt
