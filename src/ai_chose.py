from enum import Enum
from typing import List, Dict
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel
import argparse
import json

# 定義 Pydantic 模型來結構化輸出
class ChosenNewsItem(BaseModel):
    link: str
    title: str
    ai_reason: str

class ChosenNewsParameters(BaseModel):
    chosen_news: List[ChosenNewsItem]

class AIChose:
    def __init__(self, source: str, feed_name: str, n: int):
        self.source = source
        self.feed_name = feed_name
        self.n = n
        
        # 路徑相關參數
        self.data_dir = "./data"
        self.news_dir = f"{self.data_dir}/news"
        self.news_chosen_dir = f"{self.data_dir}/news_chosen"
        self.prompt_dir = "./prompt"
        
        self.input_filename = f"{self.news_dir}/{source}_{feed_name}.csv"
        self.output_filename = f"{self.news_chosen_dir}/{source}_{feed_name}.csv"
        self.prompt_template_path = f"{self.prompt_dir}/chose_news.txt"
        
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key
        self.prompt_template = self.load_prompt_template()

    def load_prompt_template(self):
        with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def load_news(self) -> pd.DataFrame:
        return pd.read_csv(self.input_filename)

    def choose_important_news(self, news_df: pd.DataFrame) -> List[Dict[str, any]]:
        total_news = len(news_df)
        news_list = news_df.to_dict(orient='records')

        prompt = self.prompt_template.format(n=self.n, news_list=json.dumps(news_list, ensure_ascii=False, indent=2), total_news=total_news)

        client = openai.OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a professional news editor skilled at selecting important and valuable news."},
                {"role": "user", "content": prompt}
            ],
            tools=[
                openai.pydantic_function_tool(
                    ChosenNewsParameters, 
                    name="output_chosen_news", 
                    description="Select the most important news with original url links from the original list and the reasons they are important."
                )
            ]
        )

        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "output_chosen_news":
            chosen_news = json.loads(tool_call.function.arguments)['chosen_news']
            print("API returned chosen_news:", chosen_news)
            return chosen_news
        else:
            print("未找到預期的函數調用")
            return []

    def save_to_csv(self, data_frame: pd.DataFrame):
        os.makedirs(os.path.dirname(self.output_filename), exist_ok=True)
        data_frame.to_csv(self.output_filename, index=False)

    def run(self):
        news_df = self.load_news()
        print(f"載入了 {len(news_df)} 條新聞")

        chosen_news = self.choose_important_news(news_df)
        print(f"選擇了 {len(chosen_news)} 條重要新聞")

        if chosen_news:
            chosen_links = [item['link'] for item in chosen_news]
            if not all(link in news_df['link'].values for link in chosen_links):
                print("警告：某些選擇的新聞連結不在原始數據中")
                chosen_news = [item for item in chosen_news if item['link'] in news_df['link'].values]
            chosen_df = news_df[news_df['link'].isin(chosen_links)].copy()

            if chosen_df.empty:
                print("選擇的新聞DataFrame為空，請檢查連結是否正確")
                return

            # 確保 ai_reason 欄位存在
            if 'ai_reason' not in chosen_df.columns:
                chosen_df['ai_reason'] = ''

            for item in chosen_news:
                chosen_df.loc[chosen_df['link'] == item['link'], 'ai_reason'] = item['ai_reason']

            self.save_to_csv(chosen_df)
            print(f"選擇了 {len(chosen_news)} 條重要新聞，儲存至 {self.output_filename}")
        else:
            print("無法選擇重要新聞，chosen_news 為空")

# 選擇 CSV 文件
def get_news_files():
    ai_chose = AIChose("", "", 0)  # 創建一個臨時實例來訪問路徑
    return [f for f in os.listdir(ai_chose.news_dir) if f.endswith('.csv')]

def select_news_file():
    news_files = get_news_files()
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

# 輸入要選擇的新聞數量
def get_num_chosen():
    while True:
        try:
            num = int(input("請輸入要選擇的重要新聞數量: "))
            if num > 0:
                return num
            else:
                print("請輸入大於 0 的數字。")
        except ValueError:
            print("請輸入有效的數字。")

def main():
    parser = argparse.ArgumentParser(description="選擇重要新聞")
    parser.add_argument('-f', '--file', help='新聞 CSV 文件名稱')
    parser.add_argument('-n', '--num_chosen', type=int, help='選擇的重要新聞數量')
    args = parser.parse_args()

    if not args.file:
        args.file = select_news_file()

    if not args.num_chosen:
        args.num_chosen = get_num_chosen()

    source, feed_name = args.file.replace('.csv', '').split('_', 1)

    ai_chose = AIChose(source, feed_name, args.num_chosen)
    ai_chose.run()
    print(f"選擇了 {args.num_chosen} 條重要新聞，結果保存在 {ai_chose.output_filename}")

if __name__ == "__main__":
    main()