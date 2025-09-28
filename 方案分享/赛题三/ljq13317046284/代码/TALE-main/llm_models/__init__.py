from openai import OpenAI
from google.api_core import retry
import time
import torch
import requests
import google.generativeai as palm
from tqdm import tqdm
from utils import *
import random
from vllm import LLM, SamplingParams
import logging
import os

os.environ["XFORMERS_FORCE_DISABLE_SDPA"] = "1"
logger = logging.getLogger(__name__)

API_BASE = "The API BASE"
palm_api_key = ''
claude_api_key = ""
max_tokens = 1024


class HuggingFaceModel:
    def __init__(self, args):
        self.args = args
        self.model_path = f'.cache/{self.args.model}'
        # set inference params
        self.llm = LLM(
            model=self.model_path,
            tokenizer=self.model_path,
            max_model_len=2048,
            gpu_memory_utilization=0.25,
        )
        logger.info("Model loaded!")

    def inference(self, cur_sample, n_reasoning_paths):
        sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.9,
            max_tokens=max_tokens,
            repetition_penalty=1.2,
        )
        logger.info("Inference processing...")
        formatted_messages = [
            f"You are a helpful assistant.\nUser: {cur_sample[0]['prompt']}\nAssistant:"
        ]
        outputs = self.llm.generate(formatted_messages, sampling_params)
        n_input, n_output = [], []
        return [outputs.outputs[0].text.strip()], n_input, n_output

    def inference_batch(self, sample_list, n_reasoning_paths):
        sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.9,
            max_tokens=max_tokens,
            repetition_penalty=1.2,
        )
        logger.info("Inference processing...")
        formatted_messages = [
            f"You are a helpful assistant.\nUser: {sample}\nAssistant:" for sample in sample_list
        ]
        results = []
        logger.info(f"batch size: {self.args.batch_size}")
        for i in tqdm(range(0, len(sample_list), self.args.batch_size), desc="Processing", unit="batch"):
            batch = formatted_messages[i:i + self.args.batch_size]
            outputs = self.llm.generate(batch, sampling_params)
            batch_results = [output.outputs[0].text.strip() for output in outputs]
            results.extend(batch_results)
            # logger.info(batch[-1])
            # logger.info(batch_results[-1])
            del outputs
            torch.cuda.empty_cache()
        assert len(results) == len(sample_list)
        # results = [output[i][0]['generated_text'][-1]['content'] for i in range(len(output))]
        return results

    @staticmethod
    def format_message(message):
        formatted_message = ""
        for msg in message:
            role = msg["role"]
            content = msg["content"]
            formatted_message += f"{role}: {content}\n"
        return formatted_message.strip()


def call_gpt(cur_sample, n_reasoning_paths,
             api_key="your_api_key",
             model='gpt-4o-mini'):
    while True:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        data = {
            "model": model,
            "messages": [
                {"role": "system",
                 "content": "You are a helpful assistant."
                 },
                {"role": "user",
                 "content": cur_sample[0]['prompt']
                 }
            ],
            "max_tokens": max_tokens,
            "seed": 1024,
            "n": n_reasoning_paths
        }

        response = requests.post("https://aigptx.top/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            responses = response.json()
            answers = []
            for i in range(n_reasoning_paths):
                answers.append(responses['choices'][0]['message']['content'])
            n_input = responses['usage']['prompt_tokens']
            n_output = responses['usage']['completion_tokens']
            return answers, n_input, n_output
        else:
            logger.info(f"Error: {response.status_code} - {response.text}")
            time.sleep(random.uniform(1, 3))


def call_Yi_Lightning(cur_sample, n_reasoning_paths,
                      api_key='your_api_key',
                      model='yi-lightning'):
    client = OpenAI(
        api_key=api_key,
        base_url=API_BASE
    )
    while True:
        try:
            responses = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {'role': "system", "content": "You are a helpful assistant."},
                    {'role': "user", "content": cur_sample[0]['prompt']},
                ],
                # stop = stop,
                temperature=0,
                n=n_reasoning_paths,
            )
            break
        except Exception as e:
            logger.info('Error!', e)
            time.sleep(random.uniform(1, 3))
    answers = []
    for i in range(n_reasoning_paths):
        answers.append(responses.choices[i].message.content)
    n_input = responses.usage.prompt_tokens
    n_output = responses.usage.completion_tokens
    return answers, n_input, n_output


class LLMModel:
    def __init__(self, args):
        self.local = False
        self.args = args
        if 'gpt' in args.model or 'o3' in args.model or 'o1' in args.model:  # OpenAI models
            self.model = call_gpt
        elif 'yi' in args.model:
            self.model = call_Yi_Lightning
        elif 'Qwen' in args.model or 'DeepSeek' in args.model or 'Llama' in args.model:
            self.model = HuggingFaceModel(args=args)
            self.local = True
        else:
            raise NotImplementedError

    def query_batch(self, sample_list):
        # return self.model.inference_batch_new(sample_list, self.args.n)
        return self.model.inference_batch(sample_list, self.args.n)

    def query(self, sample, key='your_api_key'):
        if self.local:
            return self.model.inference(sample, n_reasoning_paths=self.args.n)
        else:
            return self.model(sample, n_reasoning_paths=self.args.n,
                              api_key=key, model=self.args.model)
