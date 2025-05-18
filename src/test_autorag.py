from dotenv import load_dotenv
from autorag.evaluator import Evaluator

load_dotenv()

evaluator = Evaluator(qa_data_path='../data/eli5_data/qa_sample.parquet', 
                      corpus_data_path='../data/eli5_data/corpus.parquet',
                      project_dir='../project_dir')

evaluator.start_trial('../config.yaml', skip_validation=True)
