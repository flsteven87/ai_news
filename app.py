import streamlit as st
import pandas as pd
import os
from pathlib import Path

# 讀取指定的新聞數據
def load_news(file_name):
    return pd.read_csv(file_name)

# 讀取重要新聞數據
def load_important_news(file_name):
    return pd.read_csv(os.path.join('./data/news_chosen', file_name))

# 獲取 data/news/ 目錄下的所有 CSV 文件
def get_news_files():
    return [f for f in os.listdir('./data/news') if f.endswith('.csv')]

# 生成安全的文件名
def generate_safe_filename(url):
    # 移除 "https://" 和 "http://"
    clean_url = url.replace('https://', '').replace('http://', '')
    # 替換所有非字母數字字符為下劃線
    safe_name = ''.join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in clean_url)
    # 截斷長度並添加固定的語音模型 "nova"
    return f"{safe_name[:100]}_nova.mp3"

# 主界面
def main():
    st.title('AI國際新聞摘要')

    # 側邊欄：選擇新聞列表
    st.sidebar.header("設置")
    news_files = get_news_files()
    selected_news_file = st.sidebar.selectbox("選擇新聞來源", news_files)
    
    # 從文件名中提取 source 和 feed
    file_name_parts = os.path.splitext(selected_news_file)[0].rsplit('_', 1)  # 只從右側拆分一次
    if len(file_name_parts) == 2:
        source, feed = file_name_parts
    else:
        source = file_name_parts[0]  # 如果沒有語音模型，則只有 source
        feed = ''  # feed 為空字符串

    # 讀取重要新聞數據
    important_news_data = load_important_news(selected_news_file)

    # 顯示重要新聞
    st.header("今日重要新聞")
    for index, row in important_news_data.iterrows():
        st.subheader(row['ai_title'])
        st.write(f"發布時間：{row['published']}")
        st.write(f"摘要：{row['ai_summary']}")
        
        # 使用修改後的函數生成安全的文件名，並包含 source_feed 文件夾
        audio_filename = generate_safe_filename(row['link'])
        audio_file = os.path.join("data", "news_broadcast", f"{source}_{feed}", audio_filename)
        
        if os.path.exists(audio_file):
            st.audio(audio_file, format='audio/mp3')
        else:
            st.warning(f"語音檔案不存在：{audio_file}")
        
        st.markdown(f"[閱讀全文]({row['link']})")
        st.markdown("---")

    # 顯示所有新聞
    st.header("所有新聞")
    news_data = load_news(os.path.join('./data/news', selected_news_file))
    for index, row in news_data.iterrows():
        with st.expander(f"{row['ai_title']} - {row['published']}"):
            st.write(f"摘要：{row['ai_summary']}")
            st.markdown(f"[閱讀全文]({row['link']})")

if __name__ == '__main__':
    main()