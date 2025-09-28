## Installation

### Step 1: Install VERL Framework

1. **Clone the repository with VERL submodule**:
   ```bash
   git clone --recursive https://github.com/your-username/ShorterBetter.git
   cd ShorterBetter
   ```

2. **Install VERL dependencies**:
   
   Follow the [official VERL installation guide](https://verl.readthedocs.io/en/latest/start/install.html) for detailed instructions. The basic installation involves:
   
   ```bash
   # Install from source
   cd verl
   pip install -e .
   
   # Install additional dependencies for training backends
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   pip install flash-attn --no-build-isolation
   pip install vllm>=0.8.0  # For rollout generation
   ```

### Step 2: Install ShorterBetter Dependencies

3. **Install additional ShorterBetter dependencies**:
   ```bash
   cd ..  # Back to ShorterBetter root
   pip install -r requirements.txt
   ```

## Training

### Available Training Scripts

The training scripts are located in `scripts/train/` and include:

1. **`sb_4b.sh`** - Training script for 4B parameter models

### Running Training

1. **Configure your environment variables**

2. **Customize reward function** (optional):
   - Edit `/ShorterBetter/verl/verl/workers/reward_manager/naive.py` line 244
   - Adjust `alpha`  parameters (default: alpha=0.2)

3. **Run training**:
   ```bash
   bash scripts/train/sb_4b.sh 




1. 关于缩短思维链：我们将alhpa设置成0.2， 训练一个epoch即可，可以取75步或者100步。
2. 关于强化准确率：我们将alpha设置成0.0，我们训练了15个epoch，单8*H200耗时3天。