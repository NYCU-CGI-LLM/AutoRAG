## 📂 專案目錄結構

```
your-project/
├─ app/
│  ├─ __init__.py
│  ├─ main.py          # FastAPI 入口
│  ├─ core/            # 共用工具 (config / security…)
│  ├─ schemas/         # Pydantic 資料模型
│  └─ routes/
│     ├─ __init__.py   # 聚合路由
│     ├─ auth.py       # JWT 登入 / 驗證
│     └─ items.py      # 範例受保護 API
└─ requirements.txt
```

---

## 📦 requirements.txt

```text
fastapi>=0.111
uvicorn[standard]>=0.29

# JWT 驗證
python-jose[cryptography]

# multipart/form-data 支援 (檔案上傳)
python-multipart

# 型別驗證 (FastAPI 依賴)
pydantic>=2.7

# (若已有使用) 背景佇列與監控
redis>=5.0
celery>=5.3
flower>=2.0
```

> **備註**
>
> * JWT 由 `python-jose` 提供；若要改回 PyJWT，將 `python-jose` 替換為 `PyJWT` 即可。
> * 以上檔案結構與相依套件即可完整重現「FastAPI + JWT + Redis/Celery」這組功能。
