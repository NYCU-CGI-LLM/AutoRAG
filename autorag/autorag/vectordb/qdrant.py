import logging
from datetime import datetime
import uuid
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import (
	Distance,
	VectorParams,
	PointStruct,
	PointIdsList,
	HasIdCondition,
	Filter,
	SearchRequest,
)

from typing import List, Tuple, Union, Optional, Dict, Any

from autorag.vectordb import BaseVectorStore

logger = logging.getLogger("AutoRAG")


class Qdrant(BaseVectorStore):
	def __init__(
		self,
		embedding_model: Union[str, List[dict]],
		collection_name: str,
		embedding_batch: int = 100,
		similarity_metric: str = "cosine",
		client_type: str = "docker",
		url: str = "http://localhost:6333",
		host: str = "",
		api_key: str = "",
		dimension: Optional[int] = None,
		ingest_batch: int = 64,
		parallel: int = 1,
		max_retries: int = 3,
		store_text: bool = True,  # New parameter to control whether to store original text
		use_uuid_ids: bool = True,  # New parameter to control ID format
	):
		super().__init__(embedding_model, similarity_metric, embedding_batch)

		self.collection_name = collection_name
		self.ingest_batch = ingest_batch
		self.parallel = parallel
		self.max_retries = max_retries
		self.store_text = store_text
		self.use_uuid_ids = use_uuid_ids
		self._id_mapping: Dict[str, str] = {}  # Maps original string IDs to UUID strings

		if similarity_metric == "cosine":
			distance = Distance.COSINE
		elif similarity_metric == "ip":
			distance = Distance.DOT
		elif similarity_metric == "l2":
			distance = Distance.EUCLID
		else:
			raise ValueError(
				f"similarity_metric {similarity_metric} is not supported\n"
				"supported similarity metrics are: cosine, ip, l2"
			)

		if client_type == "docker":
			self.client = QdrantClient(
				url=url,
			)
		elif client_type == "cloud":
			self.client = QdrantClient(
				host=host,
				api_key=api_key,
			)
		else:
			raise ValueError(
				f"client_type {client_type} is not supported\n"
				"supported client types are: docker, cloud"
			)

		if not self.client.collection_exists(collection_name):
			if dimension is None:
				logger.info(f"Auto-detecting embedding dimension for model: {embedding_model}")
				try:
					test_embedding_result: List[float] = self.embedding.get_query_embedding("test")
					dimension = len(test_embedding_result)
					logger.info(f"Auto-detected embedding dimension: {dimension}")
				except Exception as e:
					logger.warning(f"Failed to auto-detect dimension: {e}. Falling back to default 1536.")
					dimension = 1536
			else:
				logger.info(f"Using explicitly specified dimension: {dimension}")
			
			self.client.create_collection(
				collection_name,
				vectors_config=VectorParams(
					size=dimension,
					distance=distance,
				),
			)
		else:
			if dimension is not None:
				existing_collection = self.client.get_collection(collection_name)
				existing_dimension = existing_collection.config.params.vectors.size
				if existing_dimension != dimension:
					logger.warning(
						f"Specified dimension ({dimension}) doesn't match existing collection dimension ({existing_dimension}). "
						f"Using existing collection dimension."
					)
			
		self.collection = self.client.get_collection(collection_name)

	def _convert_id_to_qdrant_format(self, doc_id: str) -> str:
		"""Convert string ID to Qdrant-compatible format (UUID)"""
		if self.use_uuid_ids:
			# Generate deterministic UUID from string ID
			namespace = uuid.UUID('12345678-1234-5678-1234-123456789abc')
			qdrant_id = str(uuid.uuid5(namespace, doc_id))
			self._id_mapping[doc_id] = qdrant_id
			return qdrant_id
		else:
			# For integer IDs, hash the string to get a consistent integer
			return str(abs(hash(doc_id)) % (2**31))

	def _convert_ids_to_qdrant_format(self, doc_ids: List[str]) -> List[str]:
		"""Convert list of string IDs to Qdrant-compatible format"""
		return [self._convert_id_to_qdrant_format(doc_id) for doc_id in doc_ids]

	def _get_original_id(self, qdrant_id: str) -> str:
		"""Get original ID from Qdrant ID"""
		# Reverse lookup in mapping
		for orig_id, q_id in self._id_mapping.items():
			if q_id == qdrant_id:
				return orig_id
		return qdrant_id  # Fallback to qdrant_id if not found

	async def add(self, ids: List[str], texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None):
		"""
		Add documents to Qdrant with payload support
		
		Args:
			ids: List of document IDs
			texts: List of document texts
			metadata_list: Optional metadata for each document
		"""
		texts = self.truncated_inputs(texts)
		text_embeddings = await self.embedding.aget_text_embedding_batch(texts)

		# Convert IDs to Qdrant-compatible format
		qdrant_ids = self._convert_ids_to_qdrant_format(ids)

		points = []
		for i, (orig_id, qdrant_id, text, embedding) in enumerate(zip(ids, qdrant_ids, texts, text_embeddings)):
			# Create payload with text and metadata
			payload = {}
			
			# Store original ID in payload for retrieval
			payload["original_id"] = orig_id
			
			# Store original text if enabled
			if self.store_text:
				payload["text"] = text
				payload["text_length"] = len(text)
			
			# Add metadata if provided
			if metadata_list and i < len(metadata_list):
				payload.update(metadata_list[i])
			
			# Add indexing metadata
			payload.update({
				"indexed_at": datetime.utcnow().isoformat(),
				"embedding_model": getattr(self.embedding, 'model_name', 'unknown'),
				"collection_name": self.collection_name
			})
			
			points.append(PointStruct(
				id=qdrant_id,  # Use Qdrant-compatible ID
				vector=embedding,
				payload=payload
			))

		self.client.upload_points(
			collection_name=self.collection_name,
			points=points,
			batch_size=self.ingest_batch,
			parallel=self.parallel,
			max_retries=self.max_retries,
			wait=True,
		)

	async def fetch(self, ids: List[str]) -> List[List[float]]:
		# Convert IDs to Qdrant format
		qdrant_ids = self._convert_ids_to_qdrant_format(ids)
		
		# Fetch vectors by IDs
		fetched_results = self.client.retrieve(
			collection_name=self.collection_name,
			ids=qdrant_ids,
			with_vectors=True,
		)
		return list(map(lambda x: x.vector, fetched_results))

	async def fetch_with_payload(self, ids: List[str]) -> List[Dict[str, Any]]:
		"""
		Fetch documents with both vectors and payload data
		
		Args:
			ids: List of document IDs to fetch
			
		Returns:
			List of dictionaries containing id, vector, and payload
		"""
		# Convert IDs to Qdrant format
		qdrant_ids = self._convert_ids_to_qdrant_format(ids)
		
		fetched_results = self.client.retrieve(
			collection_name=self.collection_name,
			ids=qdrant_ids,
			with_vectors=True,
			with_payload=True,
		)
		
		return [
			{
				"id": result.payload.get("original_id", str(result.id)),  # Return original ID
				"vector": result.vector,
				"payload": result.payload or {}
			}
			for result in fetched_results
		]

	async def is_exist(self, ids: List[str]) -> List[bool]:
		# Convert IDs to Qdrant format
		qdrant_ids = self._convert_ids_to_qdrant_format(ids)
		
		existed_result = self.client.scroll(
			collection_name=self.collection_name,
			scroll_filter=Filter(
				must=[
					HasIdCondition(has_id=qdrant_ids),
				],
			),
		)
		# existed_result is tuple. So we use existed_result[0] to get list of Record
		existed_qdrant_ids = list(map(lambda x: str(x.id), existed_result[0]))
		return list(map(lambda q_id: q_id in existed_qdrant_ids, qdrant_ids))

	async def query(
		self, queries: List[str], top_k: int, **kwargs
	) -> Tuple[List[List[str]], List[List[float]]]:
		queries = self.truncated_inputs(queries)
		query_embeddings: List[
			List[float]
		] = await self.embedding.aget_text_embedding_batch(queries)

		search_queries = list(
			map(
				lambda x: SearchRequest(vector=x, limit=top_k, with_vector=True, with_payload=True),
				query_embeddings,
			)
		)

		search_result = self.client.search_batch(
			collection_name=self.collection_name, requests=search_queries
		)

		# Extract IDs and distances, converting back to original IDs
		ids = []
		scores = []
		for result in search_result:
			result_ids = []
			result_scores = []
			for hit in result:
				# Get original ID from payload
				original_id = hit.payload.get("original_id", str(hit.id)) if hit.payload else str(hit.id)
				result_ids.append(original_id)
				result_scores.append(hit.score)
			ids.append(result_ids)
			scores.append(result_scores)

		return ids, scores

	async def query_with_payload(
		self, queries: List[str], top_k: int, **kwargs
	) -> Tuple[List[List[Dict[str, Any]]], List[List[float]]]:
		"""
		Query with payload data included in results
		
		Args:
			queries: List of query strings
			top_k: Number of results to return
			
		Returns:
			Tuple of (results_with_payload, scores)
			where results_with_payload contains id, payload for each result
		"""
		queries = self.truncated_inputs(queries)
		query_embeddings: List[
			List[float]
		] = await self.embedding.aget_text_embedding_batch(queries)

		search_queries = list(
			map(
				lambda x: SearchRequest(vector=x, limit=top_k, with_vector=True, with_payload=True),
				query_embeddings,
			)
		)

		search_result = self.client.search_batch(
			collection_name=self.collection_name, requests=search_queries
		)

		# Extract results with payload and scores
		results_with_payload = []
		scores = []
		
		for result in search_result:
			result_list = []
			score_list = []
			
			for hit in result:
				# Get original ID from payload
				original_id = hit.payload.get("original_id", str(hit.id)) if hit.payload else str(hit.id)
				result_list.append({
					"id": original_id,
					"payload": hit.payload or {}
				})
				score_list.append(hit.score)
			
			results_with_payload.append(result_list)
			scores.append(score_list)

		return results_with_payload, scores

	async def delete(self, ids: List[str]):
		# Convert IDs to Qdrant format
		qdrant_ids = self._convert_ids_to_qdrant_format(ids)
		
		self.client.delete(
			collection_name=self.collection_name,
			points_selector=PointIdsList(points=qdrant_ids),
		)

	def delete_collection(self):
		# Delete the collection
		self.client.delete_collection(self.collection_name)
