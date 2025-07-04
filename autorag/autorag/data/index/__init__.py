from autorag.data.index.vectordb_index import vectordb_index

index_modules = {
    "vectordb": vectordb_index,
}

__all__ = ["index_modules", "vectordb_index"] 