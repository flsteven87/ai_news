import requests
import pandas as pd
import os

# 讀取 csv 檔案
df = pd.read_csv('./news/bbc.csv')

# 逐一處理每一個網址
for url in df['link']:
    # Request API with a timeout of 30 seconds
    response = requests.get(f'https://r.jina.ai/{url}', timeout=30)
    
    # 取得網址最後的部分作為檔案名稱
    filename = url.split('/')[-1]
    
    # 將回應的內容寫入檔案
    with open(f'./news_content/{filename}.txt', 'w') as f:
        f.write(response.text)