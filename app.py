import streamlit as st
import pandas as pd

# 讀取新聞數據
def load_news():
    return pd.read_csv('./news/bbc_summary.csv')

# 主界面
def main():
    st.title('實時新聞播報')

    # 加載新聞數據
    news_data = load_news()

    # 顯示每條新聞
    for index, row in news_data.iterrows():
        with st.expander(f"{row['ai_title']}"):
            st.write(f"{row['ai_summary']}")
            st.markdown(f"[閱讀全文]({row['link']})")

if __name__ == '__main__':
    main()
