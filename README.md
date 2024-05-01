# News Summarizer

News Summarizer 是一個使用 Python 開發的自動新聞摘要生成工具。該工具選定一個 RSS feed，收集新聞的元數據，並通過 JinaAI 的 API 爬取完整的新聞內容。之後，利用 OpenAI 的 API，將新聞標題和內容轉換成繁體中文的摘要。

## 功能

- 從指定的 RSS feed 自動抓取新聞。
- 使用 JinaAI 的 API 爬取並處理完整的新聞內容。
- 透過 OpenAI 的 API 將新聞標題和內容進行摘要，並自動翻譯成繁體中文。

## 安裝

要開始使用 News Summarizer，請按照以下步驟進行：

1. 克隆此儲存庫：

    ```bash
    git clone https://github.com/yourusername/news-summarizer.git
    cd news-summarizer
    ```

2. 安裝所需的依賴項：

    ```bash
    pip install -r requirements.txt
    ```

## 環境設定

請創建一個 `.env` 文件在專案根目錄中，並添加以下內容：

```plaintext
OPENAI_API_KEY='你的 OpenAI API 密鑰'
```

3. 透過 RSS 抓取新聞列表：

    ```bash
    python bbc_rss.py
    ```

4. 透過 JinaAI API 爬取新聞內文：

    ```bash
    python crawler.py
    ```

5. 透過 OpenAI API 以繁體中文總結新聞：

    ```bash
    python news_summarizer
    ```

6. 以 Streamlit 呈現新聞結果：

    ```
    streamlit run app.py
    ```