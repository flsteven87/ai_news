from dotenv import load_dotenv
from openai import OpenAI
import os
import pandas as pd
import argparse
from pathlib import Path

class AIRewrite:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI()
        self.prompt_path = "prompt/broadcast_transcript.txt"

    def rewrite_news(self, original_content: str, title: str) -> str:
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 檢查所需的鍵是否存在於提示模板中
        try:
            prompt = prompt_template.format(title=title, selected_news_items=original_content)
        except KeyError as e:
            print(f"提示模板缺少鍵: {e}")
            return ""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位專業的記者，請根據以下要求生成廣播新聞腳本，以繁體中文(zh-tw)輸出。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"重寫新聞時發生錯誤: {e}")
            return ""

    def get_news_files(self):
        return [f for f in os.listdir('./data/news_chosen') if f.endswith('.csv')]

    def select_news_file(self):
        news_files = self.get_news_files()
        print("可用的新聞文件：")
        for i, file in enumerate(news_files, 1):
            print(f"{i}. {file}")
        while True:
            try:
                choice = int(input("請選擇新聞文件（輸入數字）: ")) - 1
                if 0 <= choice < len(news_files):
                    return news_files[choice]
                else:
                    print("無效的選擇，請重試。")
            except ValueError:
                print("請輸入有效的數字。")

    def run(self, chosen_output_filename):
        selected_file = os.path.basename(chosen_output_filename)  # 確保只獲取文件名
        source, feed_name = selected_file.replace('.csv', '').split('_', 1)
        output_folder = Path(f"./data/news_rewrite/{source}_{feed_name}")  # 更新存放位置
        output_folder.mkdir(parents=True, exist_ok=True)

        # 構建對應的內容檔案路徑
        content_folder = Path(f"./data/news_content/{source}_{feed_name}")
        
        # 確保這裡的路徑正確
        news_df = pd.read_csv(os.path.join('./data/news_chosen', selected_file))

        for index, row in news_df.iterrows():
            link = row['link']
            safe_filename = self.get_safe_filename(link).replace('.txt', '')  # 移除重複的 .txt
            content_file_path = content_folder / f"{safe_filename}.txt"  # 確保這裡有 .txt

            if os.path.exists(content_file_path):
                with open(content_file_path, 'r', encoding='utf-8') as f:
                    news_content = f.read()
                rewritten_content = self.rewrite_news(news_content, row['title'])

                # 儲存重寫的內容
                with open(output_folder / f"{safe_filename}.txt", 'w', encoding='utf-8') as f:  # 更新檔名
                    f.write(rewritten_content)
                print(f"已生成重寫內容: {safe_filename}.txt")
            else:
                print(f"找不到對應的內容檔案: {content_file_path}")

    @staticmethod
    def get_safe_filename(url: str) -> str:
        url = url.split('://')[-1]
        safe_string = ''.join(c if c.isalnum() or c in '-._~' else '_' for c in url)
        return f"{safe_string[:200]}.txt"

if __name__ == "__main__":
    ai_rewrite = AIRewrite()
    ai_rewrite.run()