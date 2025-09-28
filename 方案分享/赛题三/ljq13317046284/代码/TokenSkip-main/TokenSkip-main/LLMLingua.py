import os
import json
from tqdm import tqdm
from llmlingua import PromptCompressor


def load_jsonl(file, encoding='utf-8'):
    data = []
    with open(file, 'r', encoding=encoding) as f:
        for j in f.readlines():
            j = json.loads(j)
            data.append(j)
    return data

def save_jsonl(data, output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    for item in data:
        with open(output_path, 'a+', encoding='utf-8') as f:
            line = json.dumps(item, ensure_ascii=False)
            f.write(line + '\n')

def filter_correct_outputs(input_path="outputs/Qwen3-4B/gsm8k/7b/Original/samples/predictions.jsonl",
                           output_path="outputs/Qwen3-4B/gsm8k/7b/Original/samples/predictions_correct.jsonl"):
    """
    Filter the correct outputs from the data.
    """
    data = load_jsonl(input_path)
    correct_data = []
    for i in range(len(data)):
        if data[i]['accuracy']:
            correct_data.append(data[i])
    print(f"Original Samples: {len(data)}, Correct Samples: {len(correct_data)}, Accuracy: {len(correct_data) / len(data)}")
    save_jsonl(correct_data, output_path)


def filter_formatted_outputs(input_path="outputs/Qwen3-4B/gsm8k/7b/Original/samples/predictions_correct.jsonl",
                             output_path="outputs/Qwen3-4B/gsm8k/7b/Original/samples/predictions_formatted.jsonl", model_type="qwen"):
    """
    Filter the formatted outputs from the data. Extract COT from th outputs.
    """
    data = load_jsonl(input_path)
    formatted_data = []
    for i in range(len(data)):
        if data[i]['cot_length'] > 500:
            continue
        if model_type == "llama3":
            spans = data[i]["output"].split('\n\nThe final answer is:')
            if len(spans) == 2:
                data[i]["cot"] = spans[0]
                formatted_data.append(data[i])
        elif model_type == "qwen":
            formatted_data.append(data[i])
        else:
            raise ValueError(f"Model Type {model_type} is not supported.")
    print(f"Original Samples: {len(data)}, Formatted Samples: {len(formatted_data)}")
    save_jsonl(formatted_data, output_path)

def LLMLingua(data, compression_ratio=0.5, model_type="qwen",
              llmlingua_path="/your_model_path/llmlingua-2-xlm-roberta-large-meetingbank"):
    """
    Compress the CoT outputs with LLMLingua-2.
    """
    if model_type == "llama3":
        cot_type = "cot"
    elif model_type == "qwen":
        cot_type = "model_output"
    else:
        raise ValueError(f"Model Type {model_type} is not supported.")

    llm_lingua = PromptCompressor(
        model_name=llmlingua_path,
        use_llmlingua2=True,  # Whether to use llmlingua-2
    )
    compressed_data = []
    for i in tqdm(range(len(data))):
        cot_output = data[i][cot_type]
        if model_type == "llama3":
            compressed_prompt = llm_lingua.compress_prompt(cot_output, rate=compression_ratio, force_tokens=['Step', ':'], force_reserve_digit=True, drop_consecutive=True)
        elif model_type == "qwen":
            compressed_prompt = llm_lingua.compress_prompt(cot_output, rate=compression_ratio)
        else:
            raise ValueError(f"Model Type {model_type} is not supported.")
        compressed_data_line = {
            'question': data[i]['messages'][0]['content'],
            'input': data[i]['prompt'],
            'output': data[i]['model_output'],
            'answer': data[i]['answer'],
            'model_answer': data[i]['prediction'],
            'is_correct': data[i]['accuracy'],
            'cot': data[i][cot_type],
            'compressed_cot': compressed_prompt['compressed_prompt'],
            'original_cot_tokens': compressed_prompt['origin_tokens'],
            'compressed_cot_tokens': compressed_prompt['compressed_tokens'],
            'compression_rate': compressed_prompt['rate']
        }
        compressed_data.append(compressed_data_line)
    return compressed_data


def compress_cot_outputs(input_path="outputs/Qwen3-4B/gsm8k/7b/Original/samples/predictions_formatted.jsonl",
                         output_dir="outputs/Qwen3-4B/gsm8k/7b/Compression", model_type="qwen",
                         llmlingua_path="llmlingua-2-xlm-roberta-large-meetingbank"):
    """
    Compress the CoT outputs with various compression ratios using LLMLingua-2.
    """
    data = load_jsonl(input_path)
    ratio_list = [0.9, 0.8, 0.7, 0.6, 0.5]
    for compression_ratio in ratio_list:
        output_path = os.path.join(output_dir, f"train_outputs_compressed_ratio_{compression_ratio}.jsonl")
        compressed_data = LLMLingua(data, compression_ratio=compression_ratio, model_type=model_type, llmlingua_path=llmlingua_path)
        save_jsonl(compressed_data, output_path)
        get_average_compress_rate(compressed_data)

def get_average_compress_rate(data):
    compress_rate = 0
    for i in range(len(data)):
        compress_rate += data[i]['compressed_cot_tokens'] / data[i]['original_cot_tokens']
    compress_rate = compress_rate / len(data)
    print(f"Average Compression Rate: {compress_rate}")


def data_processing_gsm8k(input_dir="outputs/Qwen3-4B/gsm8k/7b/", model_type="qwen",
                          llmlingua_path="/your_model_path/llmlingua-2-xlm-roberta-large-meetingbank"):
    """
    The overall pipeline to process the GSM8K data.
    """
    input_path = os.path.join(input_dir, "Original/train/samples/predictions.jsonl")
    correct_path = os.path.join(input_dir, "Original/train/samples/predictions_correct.jsonl")
    formatted_path = os.path.join(input_dir, "Original/train/samples/predictions_formatted.jsonl")
    compressed_dir = os.path.join(input_dir, "Compression")

    filter_correct_outputs(input_path=input_path, output_path=correct_path)
    filter_formatted_outputs(input_path=correct_path, output_path=formatted_path, model_type=model_type)
    compress_cot_outputs(input_path=formatted_path, output_dir=compressed_dir, model_type=model_type, llmlingua_path=llmlingua_path)

def data_processing_afac(input_dir="datasets/afac/", model_type="qwen",
                          llmlingua_path="/your_model_path/llmlingua-2-xlm-roberta-large-meetingbank"):
    """
    Process the AFAC dataset by compressing its Chain-of-Thought (CoT) outputs.
    """
    input_path = os.path.join(input_dir, "fineval-train-ds-cot.json")
    compressed_dir = os.path.join(input_dir, "Compression")
    os.makedirs(compressed_dir, exist_ok=True)

    # Load AFAC dataset
    with open(input_path, "r", encoding="utf-8") as f:
        afac_data = json.load(f)

    # Compress CoT outputs
    compressor = PromptCompressor(llmlingua_path)
    compressed_data = []
    for item in tqdm(afac_data, desc="Compressing AFAC CoT outputs"):
        compressed_cot = compressor.compress_prompt(item["output"])
        compressed_item = {
            "instruction": item["instruction"],
            "input": item["input"],
            "output": compressed_cot
        }
        compressed_data.append(compressed_item)

    # Save compressed results
    output_path = os.path.join(compressed_dir, "compressed_afac_cot.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(compressed_data, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    #data_processing_gsm8k()
    data_processing_afac()