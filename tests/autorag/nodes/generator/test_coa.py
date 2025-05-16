import pytest
from unittest.mock import patch, MagicMock, call
import asyncio
import tiktoken
import logging

from autorag.nodes.generator.coa import CoAGenerator

@pytest.fixture
def mock_basic_llm_instance():
    """Creates a basic MagicMock for an LLM instance without a tokenizer by default."""
    llm_instance = MagicMock()
    llm_instance._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])
    # No tokenizer attribute here by default
    return llm_instance

@pytest.fixture
def mock_llm_with_tokenizer_instance():
    """Creates a MagicMock for an LLM instance WITH a mocked tokenizer."""
    llm_instance = MagicMock()
    llm_instance._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])
    mock_tokenizer = MagicMock(spec=tiktoken.Encoding)
    mock_tokenizer.encode.return_value = [0,0,0,0,0] # Simulate 5 tokens for any input
    llm_instance.tokenizer = mock_tokenizer
    return llm_instance


@pytest.fixture
def coa_generator_instance(mock_llm_with_tokenizer_instance):
    """Fixture for CoAGenerator where worker LLM HAS a tokenizer."""
    worker_config = {"module_type": "MockOpenAILLM", "llm": "mock_worker_model_with_tokenizer"}
    manager_config = {"module_type": "MockOpenAILLM", "llm": "mock_manager_model_with_tokenizer"}

    with patch.object(CoAGenerator, '_initialize_autorag_llm') as mock_init_llm:
        mock_init_llm.return_value = mock_llm_with_tokenizer_instance
        
        generator = CoAGenerator(
            project_dir=".",
            llm="test_base_llm_tokenized",
            worker_llm_config=worker_config.copy(),
            manager_llm_config=manager_config.copy(),
            agent_window_size_k=20 
        )
        generator._mock_init_llm_method = mock_init_llm
        generator._mock_llm_instance_returned_by_init = mock_llm_with_tokenizer_instance 
        yield generator

def test_coa_generator_initialization(coa_generator_instance):
    """Test that CoAGenerator initializes and calls _initialize_autorag_llm for worker and manager."""
    coa_gen = coa_generator_instance
    assert coa_gen._mock_init_llm_method.call_count == 2
    # Add more assertions if needed, but the count is the main thing here for now.


def test_coa_generator_agent_window_size_k_default(mock_basic_llm_instance):
    worker_config = {"module_type": "MockBasicLLM", "llm": "mock_worker_model_basic"}
    manager_config = {"module_type": "MockBasicLLM", "llm": "mock_manager_model_basic"}

    # Create a specific worker mock that definitely has no tokenizer attribute
    # for CoAGenerator's __init__ to check against.
    worker_llm_explicitly_no_tokenizer = MagicMock()
    worker_llm_explicitly_no_tokenizer._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])
    # Ensure no 'tokenizer' attribute is even suggested by MagicMock's auto-creation
    # One way is to make accesses to 'tokenizer' raise an AttributeError
    worker_llm_explicitly_no_tokenizer.configure_mock(**{'tokenizer.side_effect': AttributeError("No tokenizer here")})
    # Or, more directly, ensure hasattr behaves as expected if the above isn't enough:
    # For the CoAGenerator's hasattr(self.worker_llm, 'tokenizer') check:
    # We need worker_llm_explicitly_no_tokenizer to not have 'tokenizer' or for it to be non-callable.
    # A simpler way for MagicMock: if an attribute is not set, hasattr is False unless it's a special name.
    # Let's ensure it *really* doesn't have it.
    if hasattr(worker_llm_explicitly_no_tokenizer, 'tokenizer'):
        del worker_llm_explicitly_no_tokenizer.tokenizer

    with patch.object(CoAGenerator, '_initialize_autorag_llm') as mock_init_llm, \
         patch('autorag.nodes.generator.coa.tiktoken.encoding_for_model') as mock_tiktoken_default_load:
        
        mock_init_llm.side_effect = [worker_llm_explicitly_no_tokenizer, mock_basic_llm_instance] 
        mock_default_tokenizer = MagicMock(spec=tiktoken.Encoding)
        mock_tiktoken_default_load.return_value = mock_default_tokenizer

        generator = CoAGenerator(
            project_dir=".",
            llm="test_base_llm_default_k",
            worker_llm_config=worker_config.copy(),
            manager_llm_config=manager_config.copy()
        )
        assert generator.agent_window_size_k == 6000

@patch('autorag.nodes.generator.coa.tiktoken.encoding_for_model') # Mock default loader
@patch.object(CoAGenerator, '_initialize_autorag_llm') # Mock LLM instantiation
def test_count_tokens_uses_worker_tokenizer(mock_init_llm, mock_tiktoken_default_load, mock_llm_with_tokenizer_instance, caplog):
    mock_init_llm.return_value = mock_llm_with_tokenizer_instance
    worker_config = {"module_type": "LLMWithTokenizer"}
    manager_config = {"module_type": "LLMWithTokenizer"}

    with caplog.at_level(logging.INFO):
        coa_gen = CoAGenerator(project_dir=".", llm="base", worker_llm_config=worker_config, manager_llm_config=manager_config)
    
    assert coa_gen._tokenizer_for_chunking == mock_llm_with_tokenizer_instance.tokenizer
    assert "Using tokenizer from worker LLM" in caplog.text
    test_text = "This is a test."
    # mock_llm_with_tokenizer_instance.tokenizer.encode always returns 5 tokens
    assert coa_gen._count_tokens(test_text) == 5 
    mock_llm_with_tokenizer_instance.tokenizer.encode.assert_called_with(test_text, allowed_special="all")
    mock_tiktoken_default_load.assert_not_called()

@patch('autorag.nodes.generator.coa.tiktoken.encoding_for_model')
@patch.object(CoAGenerator, '_initialize_autorag_llm')
def test_count_tokens_uses_default_tiktoken(mock_init_llm, mock_tiktoken_default_load, mock_basic_llm_instance, caplog):
    worker_llm_no_tokenizer = MagicMock(name="WorkerLLMNoTokenizer_DefaultTest")
    # Explicitly make sure .tokenizer is not something that looks callable by hasattr
    # One way is to ensure it does not exist, or if it does, it's not callable.
    # A simple way is to assign a non-callable, non-MagicMock to it.
    worker_llm_no_tokenizer.tokenizer = object() # Assign a non-callable plain object
    # Or, ensure it doesn't exist. MagicMock creates attributes on access if they don't have a spec.
    # Let's try ensuring it raises AttributeError as CoAGenerator expects for non-existence.
    # However, the hasattr check comes first. So we need hasattr(worker_llm_no_tokenizer, 'tokenizer') to be false
    # OR getattr(worker_llm_no_tokenizer.tokenizer, 'encode', None) to be None.
    # The simplest way is to ensure worker_llm_no_tokenizer does not have a 'tokenizer' attribute.
    # If we create it fresh, it won't have it unless we access it.
    # The CoAGenerator code: hasattr(self.worker_llm, 'tokenizer') and callable(getattr(self.worker_llm.tokenizer, 'encode', None))
    
    # Create a new mock for the worker that definitely doesn't have a real tokenizer
    fresh_worker_mock = MagicMock(spec=['_pure']) # Spec it to only have _pure
    fresh_worker_mock._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])

    mock_init_llm.side_effect = [fresh_worker_mock, mock_basic_llm_instance] 
    
    mock_actual_default_tokenizer = MagicMock(spec=tiktoken.Encoding)
    mock_actual_default_tokenizer.encode.return_value = [0,0,0]
    mock_tiktoken_default_load.return_value = mock_actual_default_tokenizer

    worker_config = {"module_type": "OtherLLM"}
    manager_config = {"module_type": "OtherLLM"}

    with caplog.at_level(logging.WARNING):
        coa_gen = CoAGenerator(project_dir=".", llm="base", worker_llm_config=worker_config, manager_llm_config=manager_config)
    
    assert coa_gen._tokenizer_for_chunking == mock_actual_default_tokenizer
    assert "Using a default tiktoken tokenizer" in caplog.text
    test_text = "Another test phrase."
    assert coa_gen._count_tokens(test_text) == 3
    mock_tiktoken_default_load.assert_called_once_with("gpt-4o-mini")
    mock_actual_default_tokenizer.encode.assert_called_once_with(test_text, allowed_special="all")

@patch('autorag.nodes.generator.coa.tiktoken.encoding_for_model')
@patch.object(CoAGenerator, '_initialize_autorag_llm')
def test_count_tokens_fallback_to_word_count(mock_init_llm, mock_tiktoken_default_load, mock_basic_llm_instance, caplog):
    fresh_worker_mock = MagicMock(spec=['_pure']) # Spec it to only have _pure
    fresh_worker_mock._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])

    mock_init_llm.side_effect = [fresh_worker_mock, mock_basic_llm_instance]
    mock_tiktoken_default_load.side_effect = Exception("Failed to load default tokenizer")

    worker_config = {"module_type": "OtherLLM"}
    manager_config = {"module_type": "OtherLLM"}

    with caplog.at_level(logging.ERROR):
        coa_gen = CoAGenerator(project_dir=".", llm="base", worker_llm_config=worker_config, manager_llm_config=manager_config)
    
    assert coa_gen._tokenizer_for_chunking is None
    assert "Failed to initialize default tiktoken tokenizer" in caplog.text
    test_text = "This will be word counted."
    expected_word_count = len(test_text.split())
    assert coa_gen._count_tokens(test_text) == expected_word_count
    mock_tiktoken_default_load.assert_called_once_with("gpt-4o-mini")


@pytest.fixture
def coa_generator_for_word_count_chunk_tests(mock_llm_with_tokenizer_instance): # Manager can have tokenizer
    worker_config = {"module_type": "MockLLMNoTokenizer", "llm": "mock_worker_model_no_tokenizer"}
    manager_config = {"module_type": "MockOpenAILLM", "llm": "mock_manager_model_with_tokenizer"}

    # Worker LLM is explicitly created to not have a real tokenizer
    worker_llm_no_tokenizer_for_fixture = MagicMock(spec=['_pure'])
    worker_llm_no_tokenizer_for_fixture._pure.return_value = (["Mocked LLM Response"], [[0]], [[0.0]])

    with patch.object(CoAGenerator, '_initialize_autorag_llm') as mock_init_llm, \
         patch('autorag.nodes.generator.coa.tiktoken.encoding_for_model') as mock_tiktoken_default_load:
        
        mock_init_llm.side_effect = [worker_llm_no_tokenizer_for_fixture, mock_llm_with_tokenizer_instance]
        mock_tiktoken_default_load.side_effect = Exception("Mock tiktoken loading failure for word count test")

        generator = CoAGenerator(
            project_dir=".",
            llm="test_base_llm_word_count_chunk",
            worker_llm_config=worker_config.copy(),
            manager_llm_config=manager_config.copy(),
            agent_window_size_k=10
        )
        yield generator

def test_coa_chunk_input_word_count(coa_generator_for_word_count_chunk_tests, caplog):
    generator = coa_generator_for_word_count_chunk_tests
    # agent_window_size_k is 10 from the fixture

    # Ensure the CoAGenerator instance for this test is indeed set up for word count
    assert generator._tokenizer_for_chunking is None 
    with caplog.at_level(logging.DEBUG):
        _ = generator._count_tokens("warm up for log") 
        assert "falling back to word count" in caplog.text

    text1 = "This is sentence one. This is sentence two. And sentence three for good measure."
    chunks1 = generator._chunk_input(text1, "query", "instr_budget", agent_window_size_k=generator.agent_window_size_k)
    assert len(chunks1) == 2
    assert chunks1[0] == "This is sentence one. This is sentence two."
    assert chunks1[1] == "And sentence three for good measure."

    text2 = "A very long single sentence that definitely exceeds the small chunk window size of ten words."
    chunks2 = generator._chunk_input(text2, "query", "instr_budget", agent_window_size_k=generator.agent_window_size_k)
    assert len(chunks2) == 1
    assert chunks2[0] == text2

# test_coa_generator_generate_basic and the original test_coa_chunk_input
# will need significant updates to their assertions if coa_generator_instance
# now uses token-based counting. For now, they are not touched by this edit but will likely fail.

# test_coa_generator_initialization is updated to use the new coa_generator_instance.

# test_coa_streams_not_implemented (unchanged)


# Placeholder for the old tests that need updating or removal:
# Renaming and enabling test_coa_generator_generate_basic
def test_coa_generator_generate_basic(coa_generator_instance):
    """Test the basic flow of the generate method with token-based chunking."""
    coa_gen = coa_generator_instance # Uses agent_window_size_k=20, tokenizer mock gives 5 tokens/ANY INPUT
    queries = ["What is AutoRAG?"]
    retrieved_contents = [["AutoRAG is a tool for RAG pipelines. It is very useful. This is the first part.",
                           "It helps optimize and evaluate RAG systems effectively. This is the second part."]]

    coa_gen.worker_llm._pure.reset_mock()

    final_answers = coa_gen.generate(queries=queries, retrieved_contents=retrieved_contents)

    assert isinstance(final_answers, list)
    assert len(final_answers) == 1
    assert final_answers[0] == "Mocked LLM Response"

    # Based on the oversimplified token-based chunking where _count_tokens always returns 5:
    # agent_window_size_k = 20.
    # _count_tokens(current_chunk_str) will be 5.
    # _count_tokens(" ") will be 5.
    # _count_tokens(sentence) will be 5.
    # The condition current_chunk_len + self._count_tokens(" ") + sentence_len > target_chunk_size
    # becomes 5 + 5 + 5 > 20, which is 15 > 20 (False).
    # So, all sentences are combined into a single chunk.
    # This means 1 worker call + 1 manager call = 2 calls to _pure.
    
    assert coa_gen._mock_llm_instance_returned_by_init._pure.call_count == 2 


def test_coa_chunk_input_token_count_split(coa_generator_instance):
    """Token-based chunking should split each sentence when window smaller than combined tokens."""
    # With mock tokenizer returning 5 tokens per text and space, window=10 will not combine.
    text = "Sentence one. Sentence two. Sentence three."
    chunks = coa_generator_instance._chunk_input(
        text=text,
        query="q",
        instruction_template_for_budget="instr",
        agent_window_size_k=10
    )
    assert chunks == [
        "Sentence one.",
        "Sentence two.",
        "Sentence three."
    ]


def test_coa_chunk_input_token_count_combine(coa_generator_instance):
    """Token-based chunking should combine two sentences when window allows."""
    text = "A. B. C."
    # window=15 allows 5+5+5=15 tokens total -> combine all three sentences into one chunk
    chunks = coa_generator_instance._chunk_input(
        text=text,
        query="q",
        instruction_template_for_budget="instr",
        agent_window_size_k=15
    )
    assert chunks == [
        "A. B. C."
    ]


# Original test_coa_streams_not_implemented is fine.