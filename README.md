# 高傳紘醫師個人網站

這是一個不需要資料庫或 API 金鑰、部署到 GitHub Pages 的單頁靜態網站。

- 網站：https://kenkao0127-droid.github.io/dr-kao-personal-website/
- 原始碼：https://github.com/kenkao0127-droid/dr-kao-personal-website

## 正式網站內容在哪裡

- `index.html`：頁面結構、各區塊的文字與連結。首頁選單含「醫療小故事」。
- `assets/site.css`：顏色、字型、桌面／手機版排版。
- `assets/site.js`：手機選單與演講照片放大檢視。
- `assets/images/`：形象照、官方 LINE QR Code、七張演講照片。
- `education/index.html`：醫療小故事總覽頁。LINE 圖文選單與首頁「醫療小故事」都連到這裡。
- `education/ldl-pomelo-story.html`：膽固醇與柚子的單篇故事；頁首可回到故事總覽。
- `content/website-content.md`：已發布文案的閱讀版與照片清單；一般內容修改時，先在此檔確認文字再更新網頁。

## 新增一則醫療小故事

1. 打開 `education/index.html`，複製一個 `article.story-card`。
2. 改類別、標題、兩到三行摘要，以及「閱讀故事 →」或「觀看影片 →」的網址。
3. 連到站外頁面或影片即可，不必改檢查程式。
4. 若新增的是本站頁面（`education/` 底下的 html），還要把檔名加入 `scripts/validate_site.py` 的 `PUBLISHED_HTML`，否則不會被發布。
5. 推送前仍執行本機安全檢查。不要加入表單、AI、自由文字輸入或可識別個資。

## 日後最簡單的更新方式

直接告訴小晴要改什麼即可，例如：

- 「把首頁的第一段改成……」
- 「新增這張 2027 年的演講照片，地點是……」
- 「更新官方 LINE／YouTube 連結」

我會修改原始檔、檢查手機版、提交到 GitHub；GitHub Pages 會自動更新 HTTPS 網站。

## 自己在 GitHub 網頁上更新

1. 在網站 repository 點選要修改的檔案。
2. 點右上角鉛筆圖示編輯；文字主要位在 `index.html`。
3. 上傳照片時，放在 `assets/images/`，再把對應檔名加入 `index.html` 的「醫學教育」區塊。
4. 推送前先執行下方本機安全檢查，再按 **Commit changes**。推送 `main` 後，GitHub Actions 會先執行 Gitleaks 與網站檢查，通過後才發布 GitHub Pages。掃描失敗時不更新網站；但已推送的資料仍在公開 repository，因此**推送前的本機掃描不能省略**。

## 本機預覽

在此資料夾開啟終端機後執行：

```bash
python -m http.server 4173
```

再開啟 <http://127.0.0.1:4173>。

## 公開前提醒

GitHub Pages 的公開 repository 會讓原始碼與網站圖片可被瀏覽。發布前請確認所有演講照片可公開呈現，未含患者、病歷、檢驗資料或其他可識別個資；也不要加入未確認的現職、年資、醫療成果或門診資訊。

## 發布與安全檢查

```bash
python scripts/validate_site.py
node --check assets/site.js
gitleaks dir . --redact --no-banner --ignore-gitleaks-allow
gitleaks git . --log-opts="--all" --redact --no-banner --ignore-gitleaks-allow
```

- `scripts/validate_site.py` 檢查資源、導覽、聯繫連結、生活照位置與正方形 QR Code；使用 `--build _site` 建立限定內容的發布包。
- Pages 只發布網頁、CSS、JavaScript 與網頁引用的圖片。文案來源、驗證腳本、工作流程與 README 留在原始碼庫，不加入 Pages 發布包。
- `.env`、憑證、私鑰、掃描報告、暫存檔與兩張已替換的舊圖片不納入 Git。
- 公開圖片已清除 EXIF／XMP／Photoshop 中繼資料；含旋轉資訊的照片先轉正，避免移除 EXIF 後方向錯誤。
- Gitleaks 使用標準規則與遮蔽輸出；CI 的 Gitleaks 版本與下載雜湊固定，GitHub Actions 固定至 commit SHA。
- 本網站沒有後端、AI API 呼叫、診療表單、金鑰或密碼；Google Fonts 為外部字型來源，地圖、LINE 與 YouTube 是跳轉連結。
- Gitleaks 無發現不代表絕對沒有敏感資料；新增內容與照片仍需人工確認。

## 設計與素材

版型方向參考 [Dr. Parth Portfolio Website](https://github.com/Ayush-Patel-56/dr-parth-portfolio-website)，目前網站為客製化靜態頁面。個人照片與文案的公開瀏覽不代表授權他人再利用；照片權利仍屬各原權利人。
