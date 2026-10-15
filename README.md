# CPBL Baseball Analysis
中華職棒數據分析網站，快速查看球員表現、球隊戰績、排行榜與跨年度比較，目前數據整理到2024年。

## 提供功能
- 打者、投手排行榜與資格門檻篩選
- 球員生涯數據與聯盟平均比較
- 球隊戰績、團隊數據與球員名單
- 多賽季資料切換與視覺化圖表
- 裁判好球帶判決模擬與答題紀錄

## 使用框架
- Vue 3、TypeScript、Vite
- ECharts、Three.js
- FastAPI、SQLite

## 本機啟動
```powershell
uv sync
uv run python scripts/setup_data.py --download
cd frontend
npm install
npm run dev
```
開啟 `http://localhost:5173`。

## 資料來源參考
- [CPBL Open Data（ldkrsi/cpbl-opendata）](https://github.com/ldkrsi/cpbl-opendata)
- [野球革命 Rebas](https://www.rebas.tw/)
