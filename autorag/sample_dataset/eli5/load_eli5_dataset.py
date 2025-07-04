import os
import pathlib

import click
from datasets import load_dataset


@click.command()
@click.option(
	"--save_path",
	type=str,
	default=pathlib.PurePath(__file__).parent,
	help="Path to save sample eli5 dataset.",
)
def load_eli5_dataset(save_path):
	# set file path
	file_path = "MarkrAI/eli5_sample_autorag"

	try:
		# load dataset with trust_remote_code=True to handle potential issues
		corpus_dataset = load_dataset(file_path, "corpus", trust_remote_code=True)["train"].to_pandas()
		qa_train_dataset = load_dataset(file_path, "qa", trust_remote_code=True)["train"].to_pandas()
		qa_test_dataset = load_dataset(file_path, "qa", trust_remote_code=True)["test"].to_pandas()
	except Exception as e:
		print(f"Error loading dataset with config names: {e}")
		print("Trying to load dataset without config names...")
		# Try loading without explicit config names
		try:
			dataset = load_dataset(file_path, trust_remote_code=True)
			print("Available dataset splits:", dataset.keys())
			# Handle different possible dataset structures
			if "corpus" in dataset:
				corpus_dataset = dataset["corpus"].to_pandas()
			else:
				print("Available keys:", list(dataset.keys()))
				raise ValueError("Corpus data not found in dataset")
			
			if "train" in dataset:
				qa_train_dataset = dataset["train"].to_pandas()
			else:
				qa_train_dataset = None
				
			if "test" in dataset:
				qa_test_dataset = dataset["test"].to_pandas()
			else:
				qa_test_dataset = None
				
		except Exception as e2:
			print(f"Failed to load dataset: {e2}")
			raise e2

	# save data
	if os.path.exists(os.path.join(save_path, "corpus.parquet")) is True:
		raise ValueError("corpus.parquet already exists")
	if os.path.exists(os.path.join(save_path, "qa.parquet")) is True:
		raise ValueError("qa.parquet already exists")
	
	corpus_dataset.to_parquet(os.path.join(save_path, "corpus.parquet"))
	print(f"Saved corpus dataset to {os.path.join(save_path, 'corpus.parquet')}")
	
	if qa_train_dataset is not None:
		qa_train_dataset.to_parquet(os.path.join(save_path, "qa_train.parquet"))
		print(f"Saved qa_train dataset to {os.path.join(save_path, 'qa_train.parquet')}")
	
	if qa_test_dataset is not None:
		qa_test_dataset.to_parquet(os.path.join(save_path, "qa_test.parquet"))
		print(f"Saved qa_test dataset to {os.path.join(save_path, 'qa_test.parquet')}")
	
	print("Dataset loading completed successfully!")


if __name__ == "__main__":
	load_eli5_dataset.main(standalone_mode=False)
