# baseball_analysis
專為中華職棒資料分析網站，使用Vue、FastAPI與SQLite。

請先安裝：
- uv
- Node.js 20 以上
- Git

在專案根目錄執行：
```powershell
uv sync
uv run python scripts/setup_data.py --download
cd frontend
npm install
```

## 啟動專案
每次要在 `frontend` 資料夾執行：
```powershell
npm run dev
```

`npm run dev` 會同時啟動：
- FastAPI 後端 API：`http://localhost:8000`
- Vue 前端網站：`http://localhost:5173`

啟動後開啟：
```text
http://localhost:5173
```

SQLite 資料庫會建立在 `data/cpbl.sqlite`。