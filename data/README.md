# 本機資料

這個資料夾的原始資料與 SQLite 資料庫不提交到 Git。每位協作者在自己的電腦建立一份即可。

## 建立資料庫

在專案根目錄執行：

```powershell
uv run python scripts/setup_data.py --download
```

這會下載 `ldkrsi/cpbl-opendata`，並建立：

```text
data/sources/cpbl-opendata/   # 原始 CSV
data/cpbl.sqlite              # 本機查詢資料庫
```

如果原始資料已經由其他方式放入 `data/sources/cpbl-opendata/`，可以省略 `--download`：

```powershell
uv run python scripts/setup_data.py
```

資料來源與授權請以原始資料庫的說明為準。不要把個人資料、密鑰或未確認授權的資料提交到 Git。
