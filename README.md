# CPBL Analysis
Vue 3 + FastAPI + SQLite 的中華職棒分析網站。瀏覽器不會呼叫外部資料來源；Python 將下載到本機的公開資料匯入 SQLite，Vue 只查詢本機 API。

## 第一次安裝
請先安裝 [uv](https://docs.astral.sh/uv/) 與 Node.js 20 以上版本。在專案根目錄執行：

```powershell
uv sync
cd frontend
npm install
```

## 啟動與查看
在 `frontend` 目錄執行：

```powershell
npm run dev
```

這個指令會同時啟動 FastAPI（port 8000）與 Vue/Vite。用瀏覽器開啟 Vite 顯示的網址即可。停止時，在同一個終端按 `Ctrl + C`。