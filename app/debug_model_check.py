"""
Debug script to check if model names are recognized correctly.
"""
from app.config import settings

def check_model_name(model_name):
    """Check if a model name is recognized in the configured model lists."""
    print(f"Checking model: '{model_name}'")
    print(f"Type: {type(model_name)}, Representation: {repr(model_name)}")
    
    # Check exact character by character (useful for whitespace/invisible chars)
    print("Character by character:")
    for i, char in enumerate(model_name):
        print(f"  Position {i}: '{char}' (ASCII: {ord(char)})")
    
    # Check against model lists
    in_openai = model_name in settings.OPENAI_MODELS
    in_google = model_name in settings.GOOGLE_MODELS
    in_llama = model_name in settings.LLAMA_MODELS
    
    print(f"In OpenAI models: {in_openai}")
    print(f"In Google models: {in_google}")
    print(f"In Llama models: {in_llama}")
    
    # Try case-insensitive comparison
    llama_lower = [m.lower() for m in settings.LLAMA_MODELS]
    in_llama_case_insensitive = model_name.lower() in llama_lower
    print(f"In Llama models (case-insensitive): {in_llama_case_insensitive}")
    
    # Check for closest matches
    if not in_llama:
        closest_matches = []
        for llama_model in settings.LLAMA_MODELS:
            if model_name in llama_model or llama_model in model_name:
                closest_matches.append(llama_model)
        
        if closest_matches:
            print(f"Closest matches in LLAMA_MODELS: {closest_matches}")
    
    # Print all available Llama models
    print("\nAll available LLAMA_MODELS:")
    for i, model in enumerate(settings.LLAMA_MODELS):
        print(f"  {i+1}. '{model}'")


if __name__ == "__main__":
    # Test the problematic model
    print("===== Testing 'Llama-4-Maverick-17B-128E-Instruct-FP8' =====")
    check_model_name("Llama-4-Maverick-17B-128E-Instruct-FP8")
    
    # Test a model that works
    print("\n===== Testing 'Llama-3.3-8B-Instruct' =====")
    check_model_name("Llama-3.3-8B-Instruct") 