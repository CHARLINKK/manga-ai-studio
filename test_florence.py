import sys
try:
    from transformers import AutoProcessor
    
    # Try WITHOUT trust_remote_code
    print("Testing WITHOUT trust_remote_code...")
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large")
    print("SUCCESS WITHOUT trust_remote_code!")
    
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("Testing WITH trust_remote_code...")
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
    print("SUCCESS WITH trust_remote_code!")
except Exception as e:
    print(f"FAILED WITH trust_remote_code: {e}")
