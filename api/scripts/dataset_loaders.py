#!/usr/bin/env python3
"""
Dataset loaders for benchmark datasets
Adapted from AutoRAG sample_dataset loaders
"""

import os
import sys
import pathlib
import logging
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

# Add the parent directory (api/) to Python path for imports
api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

try:
    from datasets import load_dataset
    HF_DATASETS_AVAILABLE = True
except ImportError:
    HF_DATASETS_AVAILABLE = False
    print("Warning: 'datasets' library not available. Install with: pip install datasets")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetLoader:
    """Base class for dataset loaders"""
    
    def __init__(self, name: str, hf_path: str):
        self.name = name
        self.hf_path = hf_path
    
    def load_dataset_safe(self, save_path: str) -> Tuple[bool, str]:
        """
        Safely load dataset with fallback to mock data if HuggingFace fails
        Returns: (success, error_message)
        """
        if not HF_DATASETS_AVAILABLE:
            logger.warning(f"HuggingFace datasets not available, creating mock data for {self.name}")
            return self._create_mock_data(save_path)
        
        # Try to load from HuggingFace
        success, error = self._load_from_huggingface(save_path)
        if success:
            return True, ""
        
        # If HuggingFace failed, fallback to mock data
        logger.error(f"Failed to load {self.name} from HuggingFace: {error}")
        logger.info(f"Falling back to mock data for {self.name}")
        return self._create_mock_data(save_path)
    
    def _load_from_huggingface(self, save_path: str) -> Tuple[bool, str]:
        """Load dataset from HuggingFace - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _create_mock_data(self, save_path: str) -> Tuple[bool, str]:
        """Create mock data - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _check_existing_files(self, save_path: str) -> bool:
        """Check if dataset files already exist"""
        corpus_path = os.path.join(save_path, "corpus.parquet")
        qa_path = os.path.join(save_path, "qa.parquet")
        
        if os.path.exists(corpus_path) or os.path.exists(qa_path):
            logger.warning(f"Dataset files already exist in {save_path}")
            return True
        return False


class TriviaQALoader(DatasetLoader):
    """TriviaQA dataset loader"""
    
    def __init__(self):
        super().__init__("TriviaQA", "MarkrAI/triviaqa_sample_autorag")
    
    def _load_from_huggingface(self, save_path: str) -> Tuple[bool, str]:
        try:
            corpus_dataset = load_dataset(self.hf_path, "corpus")["train"].to_pandas()
            qa_train_dataset = load_dataset(self.hf_path, "qa")["train"].to_pandas()
            qa_test_dataset = load_dataset(self.hf_path, "qa")["test"].to_pandas()
            
            os.makedirs(save_path, exist_ok=True)
            
            corpus_dataset.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            qa_train_dataset.to_parquet(os.path.join(save_path, "qa_train.parquet"), index=False)
            qa_test_dataset.to_parquet(os.path.join(save_path, "qa_test.parquet"), index=False)
            
            # Create combined QA file for compatibility
            qa_combined = pd.concat([qa_train_dataset, qa_test_dataset], ignore_index=True)
            qa_combined.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Successfully loaded {self.name} dataset from HuggingFace")
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _create_mock_data(self, save_path: str) -> Tuple[bool, str]:
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # Create mock corpus data
            corpus_data = {
                'doc_id': [f'doc_{i}' for i in range(10)],
                'contents': [f'This is document {i} about trivia topic {i}. It contains important information for answering trivia questions.' for i in range(10)],
                'metadata': [{'source': f'trivia_source_{i}', 'category': 'general'} for i in range(10)]
            }
            corpus_df = pd.DataFrame(corpus_data)
            corpus_df.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            
            # Create mock QA data
            qa_data = {
                'qid': [f'q_{i}' for i in range(5)],
                'query': [f'What is trivia question {i}?' for i in range(5)],
                'retrieval_gt': [[f'doc_{i}', f'doc_{i+1}'] for i in range(5)],
                'generation_gt': [f'Answer to trivia question {i}' for i in range(5)]
            }
            qa_df = pd.DataFrame(qa_data)
            qa_df.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Created mock {self.name} dataset")
            return True, ""
            
        except Exception as e:
            return False, str(e)


class MSMARCOLoader(DatasetLoader):
    """MS MARCO dataset loader"""
    
    def __init__(self):
        super().__init__("MS MARCO", "MarkrAI/msmarco_sample_autorag")
    
    def _load_from_huggingface(self, save_path: str) -> Tuple[bool, str]:
        try:
            corpus_dataset = load_dataset(self.hf_path, "corpus")["train"].to_pandas()
            qa_train_dataset = load_dataset(self.hf_path, "qa")["train"].to_pandas()
            qa_test_dataset = load_dataset(self.hf_path, "qa")["test"].to_pandas()
            
            os.makedirs(save_path, exist_ok=True)
            
            corpus_dataset.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            qa_train_dataset.to_parquet(os.path.join(save_path, "qa_train.parquet"), index=False)
            qa_test_dataset.to_parquet(os.path.join(save_path, "qa_test.parquet"), index=False)
            
            # Create combined QA file
            qa_combined = pd.concat([qa_train_dataset, qa_test_dataset], ignore_index=True)
            qa_combined.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Successfully loaded {self.name} dataset from HuggingFace")
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _create_mock_data(self, save_path: str) -> Tuple[bool, str]:
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # Create mock corpus data
            corpus_data = {
                'doc_id': [f'msmarco_doc_{i}' for i in range(10)],
                'contents': [f'This is MS MARCO document {i} containing search-related information for question answering tasks.' for i in range(10)],
                'metadata': [{'source': 'ms_marco', 'passage_id': i} for i in range(10)]
            }
            corpus_df = pd.DataFrame(corpus_data)
            corpus_df.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            
            # Create mock QA data
            qa_data = {
                'qid': [f'msmarco_q_{i}' for i in range(5)],
                'query': [f'What information can you find about topic {i}?' for i in range(5)],
                'retrieval_gt': [[f'msmarco_doc_{i}', f'msmarco_doc_{i+1}'] for i in range(5)],
                'generation_gt': [f'Based on the documents, topic {i} refers to...' for i in range(5)]
            }
            qa_df = pd.DataFrame(qa_data)
            qa_df.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Created mock {self.name} dataset")
            return True, ""
            
        except Exception as e:
            return False, str(e)


class HotpotQALoader(DatasetLoader):
    """HotpotQA dataset loader"""
    
    def __init__(self):
        super().__init__("HotpotQA", "gnekt/hotpotqa_small_sample_autorag")
    
    def _load_from_huggingface(self, save_path: str) -> Tuple[bool, str]:
        try:
            corpus_dataset = load_dataset(self.hf_path, "corpus")["train"].to_pandas()
            qa_validation_dataset = load_dataset(self.hf_path, "qa")["validation"].to_pandas()
            
            os.makedirs(save_path, exist_ok=True)
            
            corpus_dataset.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            qa_validation_dataset.to_parquet(os.path.join(save_path, "qa_validation.parquet"), index=False)
            qa_validation_dataset.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Successfully loaded {self.name} dataset from HuggingFace")
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _create_mock_data(self, save_path: str) -> Tuple[bool, str]:
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # Create mock corpus data
            corpus_data = {
                'doc_id': [f'hotpot_doc_{i}' for i in range(10)],
                'contents': [f'This is HotpotQA document {i} for multi-hop reasoning questions requiring information from multiple sources.' for i in range(10)],
                'metadata': [{'source': 'hotpotqa', 'title': f'Article {i}'} for i in range(10)]
            }
            corpus_df = pd.DataFrame(corpus_data)
            corpus_df.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            
            # Create mock QA data
            qa_data = {
                'qid': [f'hotpot_q_{i}' for i in range(5)],
                'query': [f'What is the connection between topic {i} and topic {i+1}?' for i in range(5)],
                'retrieval_gt': [[f'hotpot_doc_{i}', f'hotpot_doc_{i+1}', f'hotpot_doc_{i+2}'] for i in range(5)],
                'generation_gt': [f'The connection between topics {i} and {i+1} is...' for i in range(5)]
            }
            qa_df = pd.DataFrame(qa_data)
            qa_df.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Created mock {self.name} dataset")
            return True, ""
            
        except Exception as e:
            return False, str(e)


class ELI5Loader(DatasetLoader):
    """ELI5 dataset loader"""
    
    def __init__(self):
        super().__init__("ELI5", "MarkrAI/eli5_sample_autorag")
    
    def _load_from_huggingface(self, save_path: str) -> Tuple[bool, str]:
        try:
            # Try with config names first
            try:
                corpus_dataset = load_dataset(self.hf_path, "corpus", trust_remote_code=True)["train"].to_pandas()
                qa_train_dataset = load_dataset(self.hf_path, "qa", trust_remote_code=True)["train"].to_pandas()
                qa_test_dataset = load_dataset(self.hf_path, "qa", trust_remote_code=True)["test"].to_pandas()
            except Exception as e:
                logger.info(f"Failed with config names, trying without: {e}")
                # Try without config names
                dataset = load_dataset(self.hf_path, trust_remote_code=True)
                
                if "corpus" in dataset:
                    corpus_dataset = dataset["corpus"].to_pandas()
                else:
                    raise ValueError("Corpus data not found in dataset")
                
                qa_train_dataset = dataset.get("train", pd.DataFrame()).to_pandas() if "train" in dataset else None
                qa_test_dataset = dataset.get("test", pd.DataFrame()).to_pandas() if "test" in dataset else None
            
            os.makedirs(save_path, exist_ok=True)
            
            corpus_dataset.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            
            if qa_train_dataset is not None and not qa_train_dataset.empty:
                qa_train_dataset.to_parquet(os.path.join(save_path, "qa_train.parquet"), index=False)
            
            if qa_test_dataset is not None and not qa_test_dataset.empty:
                qa_test_dataset.to_parquet(os.path.join(save_path, "qa_test.parquet"), index=False)
            
            # Create combined QA file
            qa_datasets = [df for df in [qa_train_dataset, qa_test_dataset] if df is not None and not df.empty]
            if qa_datasets:
                qa_combined = pd.concat(qa_datasets, ignore_index=True)
                qa_combined.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Successfully loaded {self.name} dataset from HuggingFace")
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _create_mock_data(self, save_path: str) -> Tuple[bool, str]:
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # Create mock corpus data
            corpus_data = {
                'doc_id': [f'eli5_doc_{i}' for i in range(10)],
                'contents': [f'This is ELI5 document {i} explaining complex topics in simple terms for educational purposes.' for i in range(10)],
                'metadata': [{'source': 'eli5', 'category': 'explanation'} for i in range(10)]
            }
            corpus_df = pd.DataFrame(corpus_data)
            corpus_df.to_parquet(os.path.join(save_path, "corpus.parquet"), index=False)
            
            # Create mock QA data
            qa_data = {
                'qid': [f'eli5_q_{i}' for i in range(5)],
                'query': [f'ELI5: How does concept {i} work?' for i in range(5)],
                'retrieval_gt': [[f'eli5_doc_{i}', f'eli5_doc_{i+1}'] for i in range(5)],
                'generation_gt': [f'Concept {i} works like this: imagine it as...' for i in range(5)]
            }
            qa_df = pd.DataFrame(qa_data)
            qa_df.to_parquet(os.path.join(save_path, "qa.parquet"), index=False)
            
            logger.info(f"Created mock {self.name} dataset")
            return True, ""
            
        except Exception as e:
            return False, str(e)


# Available dataset loaders
DATASET_LOADERS = {
    'triviaqa': TriviaQALoader(),
    'msmarco': MSMARCOLoader(),
    'hotpotqa': HotpotQALoader(),
    'eli5': ELI5Loader(),
}


def load_benchmark_dataset(dataset_name: str, save_path: str) -> Tuple[bool, str]:
    """
    Load a benchmark dataset by name
    
    Args:
        dataset_name: Name of the dataset ('triviaqa', 'msmarco', 'hotpotqa', 'eli5')
        save_path: Path to save the dataset files
    
    Returns:
        Tuple of (success, error_message)
    """
    if dataset_name not in DATASET_LOADERS:
        return False, f"Unknown dataset: {dataset_name}. Available: {list(DATASET_LOADERS.keys())}"
    
    # Create save directory if it doesn't exist
    try:
        os.makedirs(save_path, exist_ok=True)
    except Exception as e:
        return False, f"Failed to create directory {save_path}: {e}"
    
    loader = DATASET_LOADERS[dataset_name]
    
    # Check if files already exist
    if loader._check_existing_files(save_path):
        return False, f"Dataset files already exist in {save_path}"
    
    return loader.load_dataset_safe(save_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load benchmark datasets')
    parser.add_argument('--dataset', required=True, choices=list(DATASET_LOADERS.keys()),
                       help='Dataset to load')
    parser.add_argument('--save_path', required=True, help='Path to save dataset')
    
    args = parser.parse_args()
    
    success, error = load_benchmark_dataset(args.dataset, args.save_path)
    if success:
        logger.info(f"Successfully loaded {args.dataset} dataset to {args.save_path}")
        sys.exit(0)
    else:
        logger.error(f"Failed to load {args.dataset}: {error}")
        sys.exit(1) 