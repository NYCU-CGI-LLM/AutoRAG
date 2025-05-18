import requests
import yaml
import argparse
import copy

def test_get_llm_info(base_url):
    url = f"{base_url}/llm"
    resp = requests.get(url, timeout=5)
    print("Status code:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Available generators:", data["available_generators"])
        print("OpenAI models:", data["openai_llm_models"])
    else:
        print("Error:", resp.text)

def test_set_yaml_config(base_url, yaml_content_str):
    url = f"{base_url}/set_yaml"
    headers = {
        "Content-Type": "application/x-yaml"  # Or "text/yaml", "application/yaml"
    }
    print(f"\nTesting POST to {url} with YAML content:")
    print("-" * 20)
    print(yaml_content_str)
    print("-" * 20)
    try:
        resp = requests.post(url, data=yaml_content_str.encode('utf-8'), headers=headers, timeout=10)
        print("Status code:", resp.status_code)
        if resp.status_code == 201:
            print("Response:", resp.json())
        else:
            print("Error:", resp.text)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")

# Default module configurations
openai_llm_module_config = {
    "module_type": "OpenAILLM",
    "llm": "gpt-4o-mini",
    "batch": 16
}

coa_generator_module_config = {
    "module_type": "CoAGenerator",
    "llm": "openai",
    "agent_window_size_k": 6000,
    "task_specific_requirement": "Answer the question based on the given passages.",
    "manager_llm_config": {
        "module_type": "openai_llm",
        "llm": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 1024
    },
    "worker_llm_config": {
        "module_type": "openai_llm",
        "llm": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 1024
    }
}

generator_node_strategy = {
    "metrics": [
        {"metric_name": "meteor"},
        {"metric_name": "rouge"}
    ]
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test API for AutoRAG set_api and llm_api')
    parser.add_argument('--base_url', type=str, default="http://localhost:8001", help='Base URL for the API server (default: http://localhost:8001 for set_api)')
    parser.add_argument('--llm', action='store_true', help='Test LLM Info API (/llm endpoint - ensure base_url points to llm_api, e.g., http://localhost:8017)')
    parser.add_argument('--set_yaml', action='store_true', help='Test /set_yaml endpoint by constructing and sending a YAML configuration.')
    parser.add_argument('--add_generator', type=str, choices=['openai', 'coa'], default=None, 
                        help='If --set_yaml is used, appends a specified generator node (choices: openai, coa). Optional.')

    args = parser.parse_args()
    
    if args.llm:
        print("--- Testing LLM Info API ---")
        test_get_llm_info(args.base_url)

    if args.set_yaml:
        print("\n--- Constructing and Testing Set YAML Config API ---")
        # Base retriever YAML (as per user's file version)
        final_yaml_data = {
            "node_lines": [
                {
                    "node_line_name": "retrieve_node_line",
                    "nodes": [
                        {
                            "node_type": "retrieval",
                            "strategy": {
                                "metrics": ["retrieval_f1", "retrieval_recall", "retrieval_ndcg", "retrieval_mrr"]
                            },
                            "modules": [
                                {"module_type": "BM25", "top_k": 3}
                            ]
                        }
                    ]
                }
            ]
        }

        generator_module_to_add = None
        generator_name = ""

        if args.add_generator == 'openai':
            generator_module_to_add = openai_llm_module_config
            generator_name = "OpenAILLM"
        elif args.add_generator == 'coa':
            generator_module_to_add = coa_generator_module_config
            generator_name = "CoAGenerator"
        
        if generator_module_to_add:
            print(f"Appending {generator_name} node...")
            generator_node_line = {
                "node_line_name": "generate_node_line", 
                "nodes": [
                    {
                        "node_type": "generator",
                        "strategy": copy.deepcopy(generator_node_strategy),
                        "modules": [copy.deepcopy(generator_module_to_add)]
                    }
                ]
            }
            final_yaml_data["node_lines"].append(generator_node_line)
        elif args.add_generator is not None:
            print(f"Warning: Unknown generator type '{args.add_generator}' specified. Sending retriever-only YAML.")
        else:
            print("No generator specified to add via --add_generator. Sending retriever-only YAML.")

        final_yaml_str = yaml.dump(final_yaml_data)
        test_set_yaml_config(args.base_url, final_yaml_str)
        