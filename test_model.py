from transformers import AutoTokenizer, AutoConfig
import torch
import os

def test_load_model():
    model_path = "./checkpoint"
    
    try:
        print("Testing model loading...")
        
        # Test 1: Check checkpoint files
        print("1. Checking checkpoint files...")
        files = os.listdir(model_path)
        print(f"   Files in checkpoint: {files}")
        
        # Test 2: Load config
        print("2. Loading config...")
        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        print(f"   Model type: {config.model_type}")
        print(f"   Architectures: {config.architectures}")
        
        # Test 3: Load tokenizer
        print("3. Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        print(f"   Tokenizer loaded successfully")
        print(f"   Vocab size: {tokenizer.vocab_size}")
        
        # Test 4: Try different loading approaches
        print("4. Trying different loading approaches...")
        
        # Approach 1: Try with ignore_mismatched_sizes
        try:
            print("   Approach 1: With ignore_mismatched_sizes...")
            from transformers import AutoModelForCausalLM
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                ignore_mismatched_sizes=True,
                torch_dtype=torch.float32
            )
            print("   Success with ignore_mismatched_sizes!")
            return True
        except Exception as e:
            print(f"   Failed: {e}")
        
        # Approach 2: Try with low_cpu_mem_usage
        try:
            print("   Approach 2: With low_cpu_mem_usage...")
            from transformers import AutoModelForCausalLM
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float32
            )
            print("   Success with low_cpu_mem_usage!")
            return True
        except Exception as e:
            print(f"   Failed: {e}")
        
        # Approach 3: Try with config
        try:
            print("   Approach 3: With config...")
            from transformers import AutoModelForCausalLM
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            print("   Success with config!")
            return True
        except Exception as e:
            print(f"   Failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_load_model()
    if success:
        print("\nModel loaded successfully!")
    else:
        print("\nFailed to load model")