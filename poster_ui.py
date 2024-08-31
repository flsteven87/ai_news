import streamlit as st
import json
import pandas as pd
from pathlib import Path

def load_summaries(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_grouped_news(poster_dir):
    grouped_news_file = poster_dir / "grouped_news.csv"
    if grouped_news_file.exists():
        return pd.read_csv(grouped_news_file)
    return None

def load_combined_news(poster_dir):
    combined_news_file = poster_dir / "Market_combined.csv"
    if combined_news_file.exists():
        return pd.read_csv(combined_news_file)
    return None

def main():
    st.title('AI國際新聞摘要')

    # 側邊欄：選擇摘要文件
    st.sidebar.header("設置")
    poster_dir = Path("./data/poster")
    summary_files = list(poster_dir.glob("*/summaries.json"))
    selected_file = st.sidebar.selectbox(
        "選擇摘要文件",
        options=summary_files,
        format_func=lambda x: x.parent.name
    )

    if selected_file:
        summaries = load_summaries(selected_file)
        grouped_news = load_grouped_news(selected_file.parent)
        combined_news = load_combined_news(selected_file.parent)

        for summary in summaries:
            st.header(summary['headline'])
            st.write(summary['main_body'])
            
            if grouped_news is not None and combined_news is not None:
                with st.expander("相關新聞"):
                    related_news = grouped_news[grouped_news['tag'] == summary['tag']]
                    for _, news in related_news.iterrows():
                        combined_info = combined_news[combined_news['link'] == news['link']]
                        if not combined_info.empty:
                            title = combined_info['title'].values[0]
                            source = combined_info['source'].values[0]
                            st.write(f"- [{title} - {source}]({news['link']})")
            
            st.markdown("---")

if __name__ == "__main__":
    main()