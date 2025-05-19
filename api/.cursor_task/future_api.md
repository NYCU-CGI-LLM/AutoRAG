
下面是除了你目前已有的 `/v1/run`、`/v1/retrieve`、`/v1/stream`、`/version` 之外，可能會需要考慮添加的 API 端點。這些接口可以幫助你更完整地管理向量資料庫、作業排程、健康檢查、異步任務，以及使用者反饋等：

• GET /health  
  – Service health check (返回服務可用性)  
  – 用途：監控系統是否正常啟動、依賴是否可用。  

• GET /v1/config  
  – Retrieve current pipeline configuration (回傳當前 pipeline 設置)  
  – 用途：方便 UI 或其它服務動態載入模型、檢索策略等參數。  

• POST /v1/embeddings  
  – Compute embeddings for arbitrary text (計算輸入文字的向量表示)  
  – 用途：支援前端或其他服務自訂檢索或微調，或單獨使用 embedding。  

• POST /v1/index  
  – Add or update documents in the vector DB (在向量庫中新增/更新文件)  
  – 用途：動態上傳新資料、更新 metadata、分頁或內容。  

• POST /v1/reindex  
  – Rebuild index for the entire corpus (重新索引整個語料庫)  
  – 用途：歷史資料結構變更後，或批量更新後需要重建。  

• POST /v1/generate  
  – Pure generation without retrieval (僅產生文字，不做檢索)  
  – 用途：純 LLM 生成場景，例如問答外的摘要或翻譯。  

• POST /v1/run_async → GET /v1/tasks/{task_id}  
  – Submit a query as an asynchronous task (以非同步任務方式提交查詢)  
  – 用途：長時間運算或批量查詢，返回 task_id 用於後續輪詢狀態/結果。  

• POST /v1/feedback  
  – Collect user feedback on generated answers (收集使用者對回應的反饋)  
  – 用途：用於後續訓練或調優 pipeline。  

• GET /v1/metrics  
  – Usage and performance metrics (使用量與效能指標)  
  – 用途：監控吞吐、延遲、錯誤率等，方便運維。  

• GET /v1/modules  
  – List available retrieval/generation modules (列出可用的檢索或生成模組)  
  – 用途：動態組裝或調整 pipeline，展示給前端選擇。  

• GET /v1/docs  
  – List indexed documents (查看目前已編入索引的文件清單)  
  – 用途：後台管理、資料審核、刪除操作前確認。  

• DELETE /v1/docs/{doc_id}  
  – Remove a document from the index (從向量庫中刪除指定文件)  
  – 用途：清理或下線錯誤／過時的文件。  

這些建議可依需求擴充，也能配合 Celery、Prometheus、API Gateway 等周邊生態做更完整的異步任務管理與監控。
