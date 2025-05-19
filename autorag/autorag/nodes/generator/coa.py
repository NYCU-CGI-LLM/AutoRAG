from typing import List, Dict, Optional, Any, Tuple, Callable
import re
import importlib
from autorag.nodes.generator.base import BaseGenerator
import autorag.nodes.generator as ag_generators
import logging
import tiktoken
import pandas as pd
from autorag.utils.util import result_to_dataframe

# Mapping from common YAML module_type strings to actual class names
YAML_TO_CLASS_NAME_MAP = {
    "openai_llm": "OpenAILLM",
    "vllm_llm": "Vllm",
    "vllm_api": "VllmAPI",
    "llama_index_llm": "LlamaIndexLLM"
}

# Add logger for the module
logger = logging.getLogger("AutoRAG")

class CoAGenerator(BaseGenerator):
    # ANSI Color Codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    RESET = '\033[0m'

    def __init__(self, project_dir: str, llm: str, **kwargs):
        self.project_dir = project_dir
        super().__init__(project_dir=project_dir, llm=llm, **kwargs)
        
        # 從 kwargs 初始化 CoA 參數
        self.agent_window_size_k = kwargs.get('agent_window_size_k', 6000) # default value
        self.worker_llm_config = kwargs.get('worker_llm_config', {})
        self.manager_llm_config = kwargs.get('manager_llm_config', {})
        
        # NEW: Get task_specific_requirement from kwargs for the manager prompt
        self.task_specific_requirement = kwargs.get('task_specific_requirement', "")

        # Instantiate worker and manager LLMs using their AutoRAG module configurations
        self.worker_llm = self._initialize_autorag_llm(self.worker_llm_config)
        self.manager_llm = self._initialize_autorag_llm(self.manager_llm_config)
        
        # Initialize tokenizer for chunking based on worker_llm type
        self._tokenizer_for_chunking = None
        if hasattr(self.worker_llm, 'tokenizer') and callable(getattr(self.worker_llm.tokenizer, 'encode', None)):
            # Primarily for OpenAILLM and similar that expose a tiktoken-like tokenizer
            self._tokenizer_for_chunking = self.worker_llm.tokenizer
            logger.info(f"CoAGenerator: Using tokenizer from worker LLM ({type(self.worker_llm).__name__}) for chunking.")
        else:
            # Fallback for other LLM types (Vllm, VllmAPI, LlamaIndexLLM, etc.)
            default_tokenizer_model = "gpt-4o-mini" # A modern, common tokenizer
            try:
                self._tokenizer_for_chunking = tiktoken.encoding_for_model(default_tokenizer_model)
                logger.warning(
                    f"{self.YELLOW}CoAGenerator: Worker LLM type {type(self.worker_llm).__name__} "
                    f"does not expose a 'tokenizer.encode' method directly. "
                    f"Using a default tiktoken tokenizer ('{default_tokenizer_model}') for _count_tokens during chunking. "
                    f"Chunking precision for '{type(self.worker_llm).__name__}' might vary if its native tokenization differs.{self.RESET}"
                )
            except Exception as e:
                logger.error(f"{self.RED}CoAGenerator: Failed to initialize default tiktoken tokenizer ('{default_tokenizer_model}'): {e}. "
                               f"Chunking will use word count as a last resort.{self.RESET}")
                # self._tokenizer_for_chunking remains None

        # UPDATED: Default worker prompt based on COA_WORKER_PROMPT
        self.iw_template = kwargs.get('worker_instructions_template', 
                                      "{chunk}\\n"
                                      "Here is the summary of the previous source text: {prev_cu}\\n"
                                      "Question: {query}\\n"
                                      "You need to read current source text and summary of previous source text (if any) and generate a summary to include them both.\\n"
                                      "Later, this summary will be used for other agents to answer the Query, if any.\\n"
                                      "So please write the summary that can include the evidence for answering the Query:")
        
        # UPDATED: Default manager prompt based on COA_MANAGER_PROMPT
        self.im_template = kwargs.get('manager_instructions_template',
                                      "{task_specific_requirement}\\n"
                                      "The following are given passages.\\n"
                                      "However, the source text is too long and has been summarized.\\n"
                                      "You need to answer based on the summary: \\n"
                                      "{final_cu}\\n"
                                      "Question: {query}\\n"
                                      "Answer:")
        
        # 假設有一個詞元計數器函數，例如來自 tiktoken
        # self.tokenizer = tiktoken.encoding_for_model(self.worker_llm_config.get("model_name", "gpt-3.5-turbo"))

    def _initialize_autorag_llm(self, llm_config: Dict) -> Any:
        """Dynamically instantiates an AutoRAG LLM module."""
        if not llm_config or "module_type" not in llm_config:
            raise ValueError("LLM configuration must specify 'module_type' for worker/manager_llm_config.")

        llm_config_copy = llm_config.copy() # Work with a copy
        yaml_module_type = llm_config_copy.pop("module_type")
        
        class_name_str = YAML_TO_CLASS_NAME_MAP.get(yaml_module_type, yaml_module_type)
        
        if not hasattr(ag_generators, class_name_str):
            raise ImportError(
                f"LLM class '{class_name_str}' (mapped from YAML type '{yaml_module_type}') not found in autorag.nodes.generator module. "
                f"Ensure it's imported in autorag.nodes.generator.__init__.py and YAML 'module_type' is known or matches a class name."
            )
        llm_class = getattr(ag_generators, class_name_str)

        constructor_kwargs = llm_config_copy # Use the rest of the popped config for kwargs
        try:
            return llm_class(project_dir=self.project_dir, **constructor_kwargs)
        except TypeError as e:
            problematic_args = set(constructor_kwargs.keys())
            import inspect
            sig = inspect.signature(llm_class.__init__)
            expected_params = set(sig.parameters.keys())
            unexpected_args = problematic_args - expected_params
            missing_args = set(p for p, v in sig.parameters.items() if v.default == inspect.Parameter.empty and p != 'self' and p not in constructor_kwargs and p != 'project_dir')
            error_msg = f"Error instantiating '{class_name_str}' (from YAML type '{yaml_module_type}'). Original error: {e}."
            if unexpected_args: error_msg += f" Unexpected arguments: {unexpected_args}."
            if missing_args: error_msg += f" Missing required arguments: {missing_args}."
            error_msg += f" Processed config for constructor: {constructor_kwargs}."
            error_msg += f" Expected constructor params (excluding self, project_dir): {expected_params - {'self', 'project_dir'}}."
            raise TypeError(error_msg)

    def generate(self, queries: List[str], retrieved_contents: List[List[str]], task_requirements: List[str]) -> List[str]:
        final_answers = []
        for i, current_query in enumerate(queries):
            # Use the specific task_requirement for the current query
            current_task_requirement = task_requirements[i]
            
            retrieved_passages_for_query = retrieved_contents[i]
            x_document = "\n\n".join(retrieved_passages_for_query)

            formatted_iw = self.iw_template.format(chunk="{chunk}", prev_cu="{prev_cu}", query=current_query)
            chunks = self._chunk_input(text=x_document, 
                                       query=current_query, 
                                       instruction_template_for_budget=formatted_iw,
                                       agent_window_size_k=self.agent_window_size_k)

            current_cu = ""
            if chunks:
                for chunk_ci in chunks:
                    current_cu = self._run_agent(llm_client_instance=self.worker_llm, 
                                                 instruction_template=self.iw_template, 
                                                 prompt_format_kwargs={"chunk": chunk_ci, "prev_cu": current_cu, "query": current_query},
                                                 llm_config_for_call=self.worker_llm_config,
                                                 agent_type="Worker"
                                                 )
            
            final_answer_for_query = self._run_agent(llm_client_instance=self.manager_llm, 
                                                       instruction_template=self.im_template, 
                                                       prompt_format_kwargs={"task_specific_requirement": current_task_requirement, "final_cu": current_cu, "query": current_query},
                                                       llm_config_for_call=self.manager_llm_config,
                                                       agent_type="Manager"
                                                       )
            final_answers.append(final_answer_for_query)
            
        return final_answers

    def _run_agent(self, llm_client_instance: Any, instruction_template: str, prompt_format_kwargs: Dict, llm_config_for_call: Dict, agent_type: str) -> str:
        prompt = instruction_template.format(**prompt_format_kwargs)
        
        logger.info("")
        logger.info(f"{self.GREEN}--- {self.YELLOW}{agent_type}{self.GREEN} LLM Input ---{self.RESET}")
        logger.info(f"{self.CYAN}Prompt: {prompt}{self.RESET}")
        logger.info(f"Config for call: {llm_config_for_call}")
        logger.info(f"{self.GREEN}--- End {self.YELLOW}{agent_type}{self.GREEN} LLM Input ---{self.RESET}")
        logger.info("")
        
        try:
            if hasattr(llm_client_instance, '_pure'): # Standard for AutoRAG OpenAI, VLLM etc. with detailed output
                call_kwargs = {}
                # Parameters for the ._pure() call itself, or for the underlying LLM API call if ._pure passes them via **kwargs
                if 'temperature' in llm_config_for_call: call_kwargs['temperature'] = llm_config_for_call['temperature']
                if 'max_tokens' in llm_config_for_call: call_kwargs['max_tokens'] = llm_config_for_call['max_tokens']
                # Add other relevant parameters from llm_config_for_call that _pure might expect or pass down
                # e.g. if OpenAILLM._pure takes 'top_p', it could be added here from llm_config_for_call
                
                generated_texts, _, _ = llm_client_instance._pure(prompts=[prompt], **call_kwargs)
                response_content = generated_texts[0] if generated_texts else ""
                
            elif hasattr(llm_client_instance, 'generate') and callable(getattr(llm_client_instance, 'generate')):
                call_kwargs = {k: llm_config_for_call[k] for k in ('temperature', 'max_tokens') if k in llm_config_for_call}
                generated_texts = llm_client_instance.generate(prompts=[prompt], **call_kwargs)
                response_content = generated_texts[0] if generated_texts else ""
                
            else:
                raise NotImplementedError(
                    f"Generation method not implemented or recognized for LLM type: {type(llm_client_instance).__name__}. "
                    f"CoAGenerator supports LLMs with a '_pure' or 'generate' method."
                )

            final_response_content = response_content if response_content is not None else ""
            logger.info("")
            logger.info(f"{self.GREEN}--- {self.YELLOW}{agent_type}{self.GREEN} LLM Output ---{self.RESET}")
            logger.info(f"{self.CYAN}Response: {final_response_content}{self.RESET}")
            logger.info(f"{self.GREEN}--- End {self.YELLOW}{agent_type}{self.GREEN} LLM Output ---{self.RESET}")
            logger.info("")
            return final_response_content
        except Exception as e:
            error_message = f"Error processing with {type(llm_client_instance).__name__}: {str(e)}"
            logger.info("")
            logger.info(f"{self.RED}--- {self.YELLOW}{agent_type}{self.RED} LLM Error ---{self.RESET}")
            logger.info(f"{self.RED}{error_message}{self.RESET}")
            logger.info(f"{self.RED}--- End {self.YELLOW}{agent_type}{self.RED} LLM Error ---{self.RESET}")
            logger.info("")
            return error_message

    def _count_tokens(self, text: str) -> int:
        if self._tokenizer_for_chunking:
            return len(self._tokenizer_for_chunking.encode(text, allowed_special="all"))
        else:
            # Fallback to word count if no tokenizer is available
            logger.debug("CoAGenerator: _tokenizer_for_chunking not available, falling back to word count for _count_tokens.")
            return len(text.split())

    def _chunk_input(self, text: str, query: str, instruction_template_for_budget: str, agent_window_size_k: int) -> List[str]:
        if not text.strip(): return []
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if not sentences or (len(sentences) == 1 and not sentences[0]): return []
        chunks = []
        current_chunk_str = ""
        target_chunk_size = agent_window_size_k
        for sentence in sentences:
            if not sentence: continue
            sentence_len = self._count_tokens(sentence)
            current_chunk_len = self._count_tokens(current_chunk_str)
            if current_chunk_str and (current_chunk_len + self._count_tokens(" ") + sentence_len > target_chunk_size):
                chunks.append(current_chunk_str)
                current_chunk_str = sentence
            elif not current_chunk_str and sentence_len > target_chunk_size:
                chunks.append(sentence)
                current_chunk_str = ""
            else:
                if current_chunk_str: current_chunk_str += " " + sentence
                else: current_chunk_str = sentence
        if current_chunk_str: chunks.append(current_chunk_str)
        return chunks

    async def astream(self, prompt: str, **kwargs):
        raise NotImplementedError("CoAGenerator does not currently support astream per intermediate step. Consider non-streaming generation.")

    def stream(self, prompt: str, **kwargs):
        raise NotImplementedError("CoAGenerator does not currently support stream per intermediate step. Consider non-streaming generation.") 

    @result_to_dataframe(["generated_texts", "generated_tokens", "generated_log_probs"])
    def pure(self, previous_result: pd.DataFrame, *args, **kwargs) -> Tuple[List[str], List[str], List[List[Optional[float]]]]:
        if 'retrieved_contents' not in previous_result.columns:
            raise ValueError("Input DataFrame must contain 'retrieved_contents' column for CoAGenerator.pure().")

        # Determine the source for task requirements and queries
        if 'prompts' in previous_result.columns:
            logger.info(f"{self.CYAN}CoAGenerator: Using 'prompts' column from previous_result as dynamic 'task_specific_requirement' for each query.{self.RESET}")
            task_requirements = previous_result['prompts'].tolist()
            if 'query' not in previous_result.columns:
                raise ValueError("Input DataFrame must contain 'query' column even if 'prompts' column is used for task_specific_requirement.")
            queries = previous_result['query'].tolist()
        elif 'query' in previous_result.columns:
            logger.info(f"{self.CYAN}CoAGenerator: Using 'query' column as query and static 'task_specific_requirement' (from config: '{self.task_specific_requirement}').{self.RESET}")
            queries = previous_result['query'].tolist()
            # Use the static task_specific_requirement for all items
            task_requirements = [self.task_specific_requirement] * len(queries)
        else:
            raise ValueError("Input DataFrame must contain at least 'query' and 'retrieved_contents' columns for CoAGenerator.pure().")

        retrieved_contents = previous_result['retrieved_contents'].tolist()

        # Pass the determined task_requirements to the generate method
        generated_texts_list = self.generate(
            queries=queries, 
            retrieved_contents=retrieved_contents,
            task_requirements=task_requirements
        )

        # Match the previous behavior where generated_tokens was the same as generated_texts
        generated_tokens_list = generated_texts_list 

        # Match the previous behavior for placeholder log_probs
        # Each generated text corresponds to one list of log_probs (even if it's just [None])
        generated_log_probs_list = [[None] for _ in range(len(generated_texts_list))]

        return generated_texts_list, generated_tokens_list, generated_log_probs_list

    def _pure(self, *args, **kwargs):
        """
        Stub to satisfy BaseGenerator's abstract method _pure.
        """
        raise NotImplementedError("CoAGenerator does not support _pure directly. Use pure() instead.")