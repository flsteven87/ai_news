import schedule
import time
from src.ai_news import AINews
from src.config.log_config import setup_logger
import yaml
from pathlib import Path
from typing import Dict, List
import pandas as pd
import json
from openai import OpenAI
from pydantic import BaseModel
from datetime import datetime
from utils.file_utils import get_safe_filename, ensure_dir, get_file_path

class NewsGroup(BaseModel):
    links: List[str]
    tag: str
    importance_score: float

class NewsGroupingResult(BaseModel):
    news_groups: List[NewsGroup]

class NewsSummary(BaseModel):
    tag: str
    importance_score: float
    headline: str
    main_body: str

class Poster:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.config_path = Path("./src/config/rss_feed.yaml")
        self.keyword = "Market"  # 參數化關鍵字
        self.rss_config = self.load_rss_config()
        self.ai_news_instances: Dict[str, AINews] = {}
        self.last_processed_time: Dict[str, float] = {}
        self.valuable_news: List[NewsGroup] = []
        self.post_platforms: List[str] = []  # 可以在這裡添加不同的發布平台
        self.combined_df = None
        self.news_content_dir = ensure_dir(Path("./data/news_content"))
        self.run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.poster_dir = ensure_dir(Path(f"./data/poster/{self.run_time}"))

    def load_rss_config(self) -> Dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                full_config = yaml.safe_load(file)
            
            selected_config = {"news_sources": {}}
            
            for source, data in full_config["news_sources"].items():
                selected_feeds = [feed for feed in data["feeds"] if self.keyword in feed["name"]]
                if selected_feeds:
                    selected_config["news_sources"][source] = {
                        "name": data["name"],
                        "feeds": selected_feeds
                    }
            
            self.logger.info(f"已載入 RSS 配置，共 {len(selected_config['news_sources'])} 個來源")
            
            # 記錄所選擇的源和訂閱
            for source, data in selected_config["news_sources"].items():
                self.logger.info(f"選擇的來源: {source}")
                for feed in data["feeds"]:
                    self.logger.info(f"  - 訂閱: {feed['name']}")
            
            return selected_config
        except Exception as e:
            self.logger.error(f"載入 RSS 配置失敗：{e}")
            raise

    def initialize_ai_news_instances(self):
        for source, data in self.rss_config["news_sources"].items():
            for feed in data["feeds"]:
                key = f"{source}_{feed['name']}"
                self.ai_news_instances[key] = AINews(feed["url"], source, feed["name"])
                self.last_processed_time[key] = 0
        self.logger.info(f"Initialized {len(self.ai_news_instances)} AINews instances")

    def concat_news_data(self):
        all_news = []
        for key, ai_news in self.ai_news_instances.items():
            csv_path = Path(f"./data/news/{ai_news.source}_{ai_news.feed_name}.csv")
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    df['source'] = ai_news.source
                    df['feed'] = ai_news.feed_name
                    all_news.append(df)
                except Exception as e:
                    self.logger.error(f"Error reading CSV for {key}: {e}")
            else:
                self.logger.warning(f"CSV file not found for {key}: {csv_path}")
        
        if all_news:
            combined_df = pd.concat(all_news, ignore_index=True)
            
            # 直接在這裡保存合併的數據
            save_path = self.poster_dir / f"{self.keyword}_combined.csv"
            combined_df.to_csv(save_path, index=False, encoding='utf-8')
            self.logger.info(f"已將合併的新聞數據保存至 {save_path}")
            
            self.combined_df = combined_df
            return combined_df
        else:
            self.logger.warning("No news data found to concatenate")
            return None

    def load_prompt_template(self):
        prompt_path = Path("./prompt/group_and_tag_news.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
            # 檢查模板是否包含所需的佔位符
            if "{news_list}" not in template:
                raise ValueError("Prompt template is missing {news_list} placeholder")
            return template
        except Exception as e:
            self.logger.error(f"Error loading prompt template: {e}")
            raise

    def group_and_tag_news(self, combined_df):
        client = OpenAI()
        news_list = combined_df.to_dict(orient='records')
        
        try:
            formatted_prompt = self.load_prompt_template().format(
                news_list=json.dumps(news_list, ensure_ascii=False, indent=2)
            )
        except Exception as e:
            self.logger.error(f"Error formatting prompt template: {e}")
            return []
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                temperature=0,
                messages=[
                    {"role": "system", "content": "您是一位專業的新聞編輯，擅長分組和標記重要且有價值的新聞。"},
                    {"role": "user", "content": formatted_prompt}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "output_news_groups",
                        "description": "Output grouped and tagged news articles",
                        "parameters": NewsGroupingResult.schema()
                    }
                }]
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "output_news_groups":
                result = json.loads(tool_call.function.arguments)
                news_groups = result['news_groups']
                self.logger.info(f"Grouped news into {len(news_groups)} topics")
                
                # 直接在這裡保存分組新聞
                save_path = self.poster_dir / "grouped_news.csv"
                data = []
                for group in news_groups:
                    for link in group['links']:
                        data.append({
                            "link": link,
                            "tag": group['tag'],
                            "importance_score": group['importance_score']
                        })
                pd.DataFrame(data).to_csv(save_path, index=False, encoding='utf-8')
                self.logger.info(f"已將分組新聞保存至 {save_path}")
                
                return news_groups
            else:
                self.logger.warning("Unexpected function call in API response")
                return []
        except Exception as e:
            self.logger.error(f"Error in grouping and tagging news: {e}")
            return []

    def load_summarize_prompt_template(self):
        prompt_path = Path("./prompt/summarize_group_news.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
            if "{group_tag}" not in template or "{news_contents}" not in template:
                raise ValueError("提示模板缺少必要的佔位符")
            return template
        except Exception as e:
            self.logger.error(f"載入摘要提示模板時出錯：{e}")
            raise

    def summarize_news_groups(self):
        self.logger.info("開始為每個新聞組生成摘要")
        client = OpenAI()
        summaries = []

        for group in self.valuable_news:
            try:
                self.logger.info(f"開始為標籤 '{group['tag']}' 的新聞組生成摘要")
                group_contents = self.collect_group_contents(group)
                
                formatted_prompt = self.load_summarize_prompt_template().format(
                    group_tag=group['tag'],
                    news_contents=json.dumps(group_contents, ensure_ascii=False, indent=2)
                )

                response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    temperature=0,
                    messages=[
                        {"role": "system", "content": "您是一位專業的新聞編輯，擅長總結和提取新聞組的關鍵信息。"},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    tools=[{
                        "type": "function",
                        "function": {
                            "name": "output_news_summary",
                            "description": "輸出新聞組的摘要和關鍵點",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "headline": {"type": "string", "description": "新聞組的標題"},
                                    "main_body": {"type": "string", "description": "新聞組的主要內容摘要"},
                                    "key_points": {"type": "array", "items": {"type": "string"}, "description": "新聞組的關鍵點列表"}
                                },
                                "required": ["headline", "main_body", "key_points"]
                            }
                        }
                    }]
                )

                tool_call = response.choices[0].message.tool_calls[0]
                if tool_call.function.name == "output_news_summary":
                    result = json.loads(tool_call.function.arguments)
                    summary = NewsSummary(
                        tag=group['tag'],
                        importance_score=group['importance_score'],
                        headline=result['headline'],
                        main_body=result['main_body'],
                        key_points=result['key_points']
                    )
                    summaries.append(summary)
                else:
                    self.logger.warning("API 回應中出現意外的函數調用")

            except Exception as e:
                self.logger.error(f"為標籤 '{group['tag']}' 的新聞組生成摘要時發生錯誤: {e}")

        # 直接在這裡保存摘要
        save_path = self.poster_dir / "summaries.json"
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump([summary.dict() for summary in summaries], f, ensure_ascii=False, indent=2)
        self.logger.info(f"已將新聞摘要保存至 {save_path}")

        return summaries

    def collect_group_contents(self, group: Dict) -> List[Dict[str, str]]:
        group_contents = []
        for link in group['links']:
            try:
                # 從 combined_df 中找到對應的行
                row = self.combined_df[self.combined_df['link'] == link].iloc[0]
                source = row['source']
                feed = row['feed']
                
                # 使用 get_safe_filename 生成安全的文件名
                safe_filename = get_safe_filename(link)
                # 構建內容文件的路徑
                content_file = get_file_path(self.news_content_dir, source, feed, safe_filename)
                
                if content_file.exists():
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    group_contents.append({
                        "link": link,
                        "source": source,
                        "feed": feed,
                        "content": content
                    })
                else:
                    self.logger.warning(f"找不到內容文件: {content_file}")
            except Exception as e:
                self.logger.error(f"處理鏈接 {link} 時發生錯誤: {e}")
        
        return group_contents

    def run(self):
        self.logger.info("開始新聞處理週期")
        for key, ai_news in self.ai_news_instances.items():
            try:
                self.logger.info(f"Processing {key}")
                ai_news.run()
                self.last_processed_time[key] = time.time()
            except Exception as e:
                self.logger.error(f"Error processing {key}: {e}")

        combined_df = self.concat_news_data()
        if combined_df is not None:
            self.valuable_news = self.group_and_tag_news(combined_df)
            self.logger.info(f"將新聞分組為 {len(self.valuable_news)} 個主題")
            
            self.summarize_news_groups()
        else:
            self.logger.warning("沒有新聞數據可處理")
        
        self.logger.info("完成新聞處理週期")

def main():
    poster = Poster()
    poster.initialize_ai_news_instances()
    poster.run()
    # schedule.every(5).minutes.do(poster.run)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)

if __name__ == "__main__":
    main()