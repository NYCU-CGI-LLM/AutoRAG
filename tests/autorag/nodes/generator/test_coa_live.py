import pytest
import os
from autorag.nodes.generator.coa import CoAGenerator
from autorag.nodes.generator.openai_llm import OpenAILLM # Assuming direct import is okay

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@pytest.mark.skipif(not OPENAI_API_KEY, reason="OPENAI_API_KEY not found in environment variables, skipping live test.")
def test_coa_generator_live_openai():
    """
    Test CoAGenerator with live OpenAI LLM calls.
    This test will make actual API calls to OpenAI.
    Ensure OPENAI_API_KEY environment variable is set.
    """
    
    # Configuration for worker and manager LLMs using OpenAI
    # Make sure the model names are valid and accessible with your API key
    worker_llm_config = {
        "module_type": "openai_llm",
        "llm": "gpt-4o-mini", 
        "temperature": 0.2,
        "max_tokens": 150 
    }
    manager_llm_config = {
        "module_type": "openai_llm",
        "llm": "gpt-4o-mini", # Or a different model like gpt-4 if preferred
        "temperature": 0.2,
        "max_tokens": 250
    }

    # Instantiate CoAGenerator
    # Note: project_dir is needed by OpenAILLM for its internal workings (e.g. caching if enabled)
    # Using a temporary directory or a mock project_dir might be needed if it tries to write.
    # For simplicity, using "." assuming test is run from a context where this is okay.
    try:
        coa_gen = CoAGenerator(
            project_dir=".", 
            llm="base_llm_placeholder", # Base llm param for CoAGenerator, not directly used for worker/manager instantiation
            worker_llm_config=worker_llm_config,
            manager_llm_config=manager_llm_config,
            agent_window_size_k=50, # Adjust as needed for test content
            task_specific_requirement="Answer the question based on the given passages."
        )
    except ImportError as e:
        pytest.fail(f"Failed to import or initialize an LLM module for CoAGenerator: {e}")
    except Exception as e:
        pytest.fail(f"Failed to instantiate CoAGenerator for live test: {e}")

    # Sample queries and retrieved contents
    queries = ["What is the capital of France?", "Summarize the process of photosynthesis."]
    retrieved_contents = [
        ["France is a country in Western Europe. Its capital is Paris. Paris is known for the Eiffel Tower."],
        ["Photosynthesis is a process used by plants, algae and certain bacteria to harness energy from sunlight and turn it into chemical energy. " +
         "It involves taking in carbon dioxide and water, and using sunlight to convert these into glucose (sugar) and oxygen. " +
         "This process is crucial for life on Earth as it produces most of the oxygen in the atmosphere."]
    ]

    print("\nStarting CoAGenerator live test with OpenAI...")
    try:
        final_answers = coa_gen.generate(queries=queries, retrieved_contents=retrieved_contents)
    except Exception as e:
        pytest.fail(f"CoAGenerator's generate method failed during live test: {e}")

    print("CoAGenerator live test completed.")
    print(f"Final Answers: {final_answers}")

    # Assertions
    assert isinstance(final_answers, list), "The result should be a list."
    assert len(final_answers) == len(queries), "Number of answers should match number of queries."

    for i, answer in enumerate(final_answers):
        assert isinstance(answer, str), f"Each answer should be a string. Got: {type(answer)} for query {i}"
        assert len(answer.strip()) > 0, f"Answer for query {i} should not be empty."
        assert "error processing with" not in answer.lower(), f"Answer for query {i} seems to be an error message: {answer}"

    print("Assertions passed for CoAGenerator live test.")

# Example for VLLM (more complex setup, placeholder)
# You would need a running VLLM server with the specified model.
# @pytest.mark.skipif(not os.getenv("VLLM_API_BASE") or not os.getenv("VLLM_MODEL_NAME"), 
#                     reason="VLLM server details not found in env variables.")
# def test_coa_generator_live_vllm():
#     vllm_api_base = os.getenv("VLLM_API_BASE") # e.g., "http://localhost:8000/v1"
#     vllm_model_name = os.getenv("VLLM_MODEL_NAME") # e.g., "meta-llama/Llama-2-7b-chat-hf"

#     worker_llm_config = {
#         "module_type": "vllm_api",  # Assuming you have a vllm_api module type
#         "llm": vllm_model_name,
#         "model": vllm_model_name, # vllm_api.py seems to use 'model'
#         "api_base": vllm_api_base,
#         "temperature": 0.2,
#         "max_tokens": 150
#     }
#     manager_llm_config = {
#         "module_type": "vllm_api",
#         "llm": vllm_model_name,
#         "model": vllm_model_name,
#         "api_base": vllm_api_base,
#         "temperature": 0.2,
#         "max_tokens": 250
#     }
#     coa_gen = CoAGenerator(
#         project_dir=".",
#         llm="base_llm_placeholder",
#         worker_llm_config=worker_llm_config,
#         manager_llm_config=manager_llm_config,
#         agent_window_size_k=1000,
#         task_specific_requirement="Answer based on the provided text."
#     )
#     queries = ["Explain the concept of a Large Language Model."]
#     retrieved_contents = [["Large Language Models (LLMs) are advanced AI models trained on vast amounts of text data. " +
#                            "They can understand, generate, and manipulate human language."]]
    
#     print("\nStarting CoAGenerator live test with VLLM...")
#     final_answers = coa_gen.generate(queries=queries, retrieved_contents=retrieved_contents)
#     print("CoAGenerator live test with VLLM completed.")
#     print(f"Final Answers: {final_answers}")

#     assert isinstance(final_answers, list)
#     assert len(final_answers) == 1
#     assert isinstance(final_answers[0], str) and len(final_answers[0].strip()) > 0
#     assert "error processing with" not in final_answers[0].lower()
#     print("Assertions passed for CoAGenerator live VLLM test.")


