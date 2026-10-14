# CPBL Analysis

CPBL 棒球資料分析網站。

## 安裝步驟

以下指令請在專案根目錄 `D:\web\baseball_analysis` 執行。

### 1. 先安裝必要工具

請先安裝：

- Python 3.14
- uv
- Node.js 20 或以上
- Git

### 2. 安裝 Python 套件

```powershell
uv sync
```

### 3. 下載資料並建立資料庫

```powershell
uv run python scripts/setup_data.py --download
```

這個指令會自動完成兩件事：

1. 下載 CPBL 原始 CSV 資料
2. 建立本機 SQLite 資料庫 `data/cpbl.sqlite`

資料庫只存在自己的電腦，不需要提交到 Git。

### 4. 安裝前端套件

```powershell
cd frontend
npm install
cd ..
```

## 啟動網站

需要開兩個 PowerShell 視窗。

### 視窗一：啟動後端 API

在專案根目錄執行：

```powershell
uv run uvicorn baseball_analysis.app:app --reload --port 8000
```

看到 API 啟動後，不要關閉這個視窗。

### 視窗二：啟動前端

在專案根目錄執行：

```powershell
cd frontend
npm run dev
```

接著用瀏覽器開啟終端機顯示的網址，通常是：

```text
http://localhost:5173
```

## 之後再次開發

資料已經下載過的話，不需要重新下載。每次開發只需要開兩個視窗：

後端：

```powershell
uv run uvicorn baseball_analysis.app:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm run dev
```

## 如果資料庫不存在

執行：

```powershell
uv run python scripts/setup_data.py
```

如果原始資料也不存在，請改用：

```powershell
uv run python scripts/setup_data.py --download
```

## 分支協作注意事項

- 每個人都使用自己電腦上的 `data/cpbl.sqlite`。
- 不要提交 `data/cpbl.sqlite`。
- 不要提交 `data/sources/` 裡的下載資料。
- 修改程式碼後正常提交 `src/`、`frontend/`、`scripts/` 和 README 即可。
