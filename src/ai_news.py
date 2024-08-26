from __future__ import annotations
import os
import requests
import pandas as pd
import feedparser
from typing import Dict, List, Optional
import argparse
from dotenv import load_dotenv
import openai
import json
import yaml
from pathlib import Path
from src.config.log_config import setup_logger
import time
from ratelimit import limits, sleep_and_retry
import random

# 初始化日誌記錄器
logger = setup_logger(__name__)

class AINewsException(Exception):
    """自定義 AINews 異常類"""
    pass

class AINews:
    def __init__(self, rss_feed_url: str, source: str, feed_name: str, re_fetch: bool = False, re_summarize: bool = False, use_proxy: bool = False):
        self.rss_feed_url = rss_feed_url
        self.source = source
        self.feed_name = feed_name
        self.data_dir = Path("./data")
        self.news_dir = self.data_dir / "news"
        self.news_content_dir = self.data_dir / "news_content"
        self.filename = self.news_dir / f"{source}_{feed_name}.csv"
        self.content_folder = self.news_content_dir / f"{source}_{feed_name}"
        self.config_path = Path("./src/config/rss_feed.yaml")
        self.re_fetch = re_fetch
        self.re_summarize = re_summarize
        self.use_proxy = use_proxy
        self.proxies = [
            {'http': '138.197.102.119:80'},
            {'http': '160.248.189.95:3128'},
            {'http': '160.248.93.134:3128'},
            {'http': '103.216.50.11:8080'},
            {'http': '124.236.25.252:8080'},
            {'http': '38.242.199.124:8089'},
            {'http': '160.248.93.158:3128'},
            {'http': '116.169.54.253:8080'},
            {'http': '160.248.186.67:3128'},
            {'http': '190.186.18.161:999'},
        ]
        load_dotenv()
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        self.client = openai.OpenAI()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "output_title_and_summary",
                    "description": "產生繁體中文標題及總結後，將它們做為參數呼叫此function。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The chinese title of news."
                            },
                            "summary": {
                                "type": "string",
                                "description": "The chinese summary of news."
                            }
                        },
                        "required": ["title", "summary"],
                    },
                },
            },
        ]
    
    def parse_feed(self) -> Dict:
        try:
            feed = feedparser.parse(self.rss_feed_url)
            if feed.bozo:
                raise AINewsException(f"Error parsing the feed: {feed.bozo_exception}")

            parsed_feed = {
                "feed_title": feed.feed.get('title', 'No title'),
                "feed_subtitle": feed.feed.get('subtitle', 'N/A'),
                "feed_link": feed.feed.get('link', 'No link'),
                "feed_published": feed.feed.get('published', 'No publish date'),
                "entries": []
            }

            for entry in feed.entries:
                parsed_feed['entries'].append({
                    "title": entry.get('title', 'No title'),
                    "summary": entry.get('summary', entry.get('description', 'No summary available')),
                    "link": entry.get('link', 'No link'),
                    "published": entry.get('published', entry.get('updated', 'No publish date'))
                })

            return parsed_feed
        except Exception as e:
            logger.error(f"Failed to parse feed: {e}")
            raise AINewsException(f"Failed to parse feed: {e}")

    @sleep_and_retry
    @limits(calls=20, period=60)  # 每分鐘 20 次請求
    def fetch_single_news(self, entry: Dict) -> None:
        safe_filename = self.get_safe_filename(entry['link'])
        file_path = self.content_folder / safe_filename

        if not self.re_fetch and file_path.exists():
            logger.info(f"跳過：{entry['title']} - 檔案已存在。")
            return

        jina_reader_url = f"https://r.jina.ai/{entry['link']}"
        
        if self.use_proxy:
            for _ in range(len(self.proxies)):
                proxy = random.choice(self.proxies)
                try:
                    response = requests.get(jina_reader_url, proxies={'http': proxy['http']}, timeout=100)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    logger.warning(f"使用代理 {proxy['http']} 失敗：{e}")
                    continue
            else:
                logger.error(f"所有代理都失敗，無法爬取：{entry['title']}")
                return
        else:
            try:
                response = requests.get(jina_reader_url, timeout=100)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"爬取內容失敗：{entry['title']} - URL：{entry['link']} - 錯誤：{e}")
                return

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"已爬取：{entry['title']} - 發布時間：{entry['published']} - URL：{entry['link']} - 狀態：{response.status_code}")

    def fetch_news_content(self, entries: List[Dict]) -> None:
        self.content_folder.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            safe_filename = self.get_safe_filename(entry['link'])
            file_path = self.content_folder / safe_filename

            if not self.re_fetch and file_path.exists():
                logger.info(f"跳過：{entry['title']} - 檔案已存在。")
                continue

            self.fetch_single_news(entry)
            time.sleep(3)  # 只有在實際爬取時才等待 3 秒

    def save_to_csv(self, data_frame: pd.DataFrame) -> None:
        try:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            data_frame.to_csv(self.filename, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {len(data_frame)} entries to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
            raise AINewsException(f"Failed to save CSV: {e}")

    @staticmethod
    def get_safe_filename(url: str) -> str:
        url = url.split('://')[-1]
        safe_string = ''.join(c if c.isalnum() or c in '-._~' else '_' for c in url)
        return f"{safe_string[:200]}.txt"

    def summarize_news(self, title: str, news_content: str) -> tuple[str, str]:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位專業的記者，你的目標是以繁體中文總結一個英文報導，包含一個繁體中文標題及繁體文總結，用戶透過你的總結能很明確的知道這篇新聞探討的議題及重點是什麼，來決定他們要不要閱讀完整的內文。"},
                    {"role": "user", "content": f"title: {title}, content: {news_content}"}
                ],
                tools=self.tools,
                tool_choice="auto"
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if tool_calls:
                for tool_call in tool_calls:
                    function_args = json.loads(tool_call.function.arguments)
                    ai_title = function_args.get("title")
                    ai_summary = function_args.get("summary")
                    return ai_title, ai_summary
            raise AINewsException("No valid response from AI model")
        except Exception as e:
            logger.error(f"Error in summarize_news: {e}")
            return "", ""

    def run(self) -> None:
        try:
            feed_data = self.parse_feed()
            if not feed_data['entries']:
                logger.error("No entries found in the feed. Exiting.")
                return

            entries_df = pd.DataFrame(feed_data['entries'])
            self.fetch_news_content(feed_data['entries'])
            
            # 檢查是否已存在摘要資料
            existing_df = None
            if not self.re_summarize and self.filename.exists():
                existing_df = pd.read_csv(self.filename)
            
            for index, news in entries_df.iterrows():
                title = news['title']
                safe_link = self.get_safe_filename(news["link"])
                file_path = self.content_folder / safe_link
                
                # 檢查是否需要摘要
                if not self.re_summarize and existing_df is not None and news['link'] in existing_df['link'].values:
                    existing_row = existing_df[existing_df['link'] == news['link']].iloc[0]
                    if existing_row['ai_title'] != '處理失敗':
                        entries_df.loc[index, 'ai_title'] = existing_row['ai_title']
                        entries_df.loc[index, 'ai_summary'] = existing_row['ai_summary']
                        logger.info(f"Skipped summarization: {existing_row['ai_title']}")
                        continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        news_content = f.read()
                    
                    ai_title, ai_summary = self.summarize_news(title, news_content)
                    if ai_title == '處理失敗' or not ai_title or not ai_summary:
                        raise Exception("摘要生成失敗")
                    entries_df.loc[index, 'ai_title'] = ai_title
                    entries_df.loc[index, 'ai_summary'] = ai_summary
                    logger.info(f"Processed: {ai_title}")
                except Exception as e:
                    logger.error(f"Error processing {title}: {e}")
                    entries_df.loc[index, 'ai_title'] = "處理失敗"
                    entries_df.loc[index, 'ai_summary'] = f"處理過程中發生錯誤: {str(e)}"

            self.save_to_csv(entries_df)
            logger.info(f"Successfully saved results to {self.filename}")
        except AINewsException as e:
            logger.error(f"AINews error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in run method: {e}")

def load_rss_config() -> Dict:
    try:
        with open('./src/config/rss_feed.yaml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load RSS config: {e}")
        raise AINewsException(f"Failed to load RSS config: {e}")

def get_user_choice(options: List[str], prompt: str) -> Optional[int]:
    for i, option in enumerate(options, 1):
        logger.info(f"{i}. {option}")
    choice = input(prompt)
    try:
        index = int(choice) - 1
        if 0 <= index < len(options):
            return index
        logger.error("Invalid choice")
    except ValueError:
        logger.error("Please enter a valid number")
    return None

def main():
    try:
        rss_config = load_rss_config()

        parser = argparse.ArgumentParser(description="Process RSS feed URL and summarize news.")
        parser.add_argument('-s', '--source', choices=list(rss_config['news_sources'].keys()), help='Choose news source')
        parser.add_argument('-f', '--feed', help='Choose specific feed')
        parser.add_argument('-ff', '--force-fetch', action='store_true', help='Force fetch all news content')
        parser.add_argument('-p', '--use-proxy', action='store_true', help='Use proxy for fetching news content')
        args = parser.parse_args()

        if not args.source:
            source_options = [source['name'] for source in rss_config['news_sources'].values()]
            source_index = get_user_choice(source_options, "Enter the number of the news source to use: ")
            if source_index is None:
                return
            args.source = list(rss_config['news_sources'].keys())[source_index]

        source = rss_config['news_sources'][args.source]
        logger.info(f"Selected news source: {source['name']}")

        if not args.feed:
            feed_options = [feed['name'] for feed in source['feeds']]
            feed_index = get_user_choice(feed_options, "Enter the number of the feed to use: ")
            if feed_index is None:
                return
            args.feed = source['feeds'][feed_index]['name']

        feed = next((f for f in source['feeds'] if f['name'] == args.feed), None)
        if not feed:
            raise AINewsException(f"Cannot find feed named {args.feed} in {args.source}")

        rss_feed_url = feed['url']
        logger.info(f"Selected feed: {feed['name']}")

        ai_news = AINews(rss_feed_url, args.source, args.feed, re_fetch=args.force_fetch, use_proxy=args.use_proxy)
        ai_news.run()
    except AINewsException as e:
        logger.error(f"AINews error in main: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")

if __name__ == "__main__":
    main()