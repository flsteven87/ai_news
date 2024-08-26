import os
import requests
import pandas as pd
import feedparser
import time
import random
import logging
from typing import Dict, List, Optional
import argparse
from dotenv import load_dotenv
import openai
import json

# Initialize the logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AINews:
    def __init__(self, rss_feed_url: str, source: str, feed_name: str, re_fetch: bool = False, re_summarize: bool = True):
        self.rss_feed_url = rss_feed_url
        self.source = source
        self.feed_name = feed_name
        self.filename = f"./data/news/{source}_{feed_name}.csv"
        self.re_fetch = re_fetch
        self.re_summarize = re_summarize
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
        feed = feedparser.parse(self.rss_feed_url)
        if feed.bozo:
            logger.error(f"Error parsing the feed: {feed.bozo_exception}")
            return {"feed_title": "No title", "feed_subtitle": "N/A", "feed_link": "No link", "feed_published": "No publish date", "entries": []}

        parsed_feed = {
            "feed_title": feed.feed.get('title', 'No title'),
            "feed_subtitle": feed.feed.get('subtitle', 'N/A'),
            "feed_link": feed.feed.get('link', 'No link'),
            "feed_published": feed.feed.get('published', 'No publish date'),
            "entries": []
        }

        for entry in feed.entries:
            title = entry.get('title', 'No title')
            link = entry.get('link', 'No link')
            summary = entry.get('summary', entry.get('description', 'No summary available'))
            published = entry.get('published', entry.get('updated', 'No publish date'))

            parsed_feed['entries'].append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published
            })

        return parsed_feed

    def fetch_news_content(self, entries: List[Dict]):
        content_folder = f"./data/news_content/{self.source}_{self.feed_name}"
        os.makedirs(content_folder, exist_ok=True)  # 確保資料夾存在

        for entry in entries:
            safe_filename = entry['link'].replace("https://", "").replace("http://", "").replace("/", "_")  # 修正命名方式
            file_path = f'{content_folder}/{safe_filename}.txt'
            
            # 根據 re_fetch 參數決定是否重爬新聞
            if not self.re_fetch and os.path.exists(file_path):
                print(f"Skipping: {entry['title']} - File already exists.")
                continue
            
            try:
                print(f"Crawling: {entry['title']} - Published: {entry['published']} - URL: {entry['link']}")
                with open(file_path, 'w', encoding='utf-8') as f:  # 確保使用相同的命名方式
                    response = requests.get(f"https://r.jina.ai/{entry['link']}", timeout=100)
                    f.write(response.text)
            except requests.exceptions.RequestException as e:
                print(f"Failed to crawl content for: {entry['title']} - URL: {entry['link']} - Error: {e}")

    def save_to_csv(self, data_frame: pd.DataFrame):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        data_frame.to_csv(self.filename, index=False)

    @staticmethod
    def get_safe_filename(url: str) -> str:
        # 移除協議前綴（如 http:// 或 https://）
        url = url.split('://')[-1]
        # 替換不安全的字符為底線
        safe_string = ''.join(c if c.isalnum() or c in '-._~' else '_' for c in url)
        return f"{safe_string[:200]}.txt"  # 限制檔案名長度

    def summarize_news(self, title, news_content):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位專業的記者，你的目標是以繁體中文總結一個英文報導，包含一個繁體中文標題及繁體���文總結，用戶透過你的總結能很明確的知道這篇新聞探討的議題及重點是什麼，來決定他們要不要閱讀完整的內文。"},
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
        except Exception as e:
            print(f"Error: {e}")
            ai_title = ""
            ai_summary = ""

        return ai_title, ai_summary

    def run(self):
        feed_data = self.parse_feed()
        if not feed_data['entries']:
            logger.error("No entries found in the feed. Exiting.")
            return

        entries_df = pd.DataFrame(feed_data['entries'])
        self.save_to_csv(entries_df)
        self.fetch_news_content(feed_data['entries'])
        for index, news in entries_df.iterrows():
            title = news['title']
            # 從 news_content folder 內讀取新聞內容
            safe_link = news["link"].replace("https://", "").replace("http://", "").replace("/", "_")  # 修正命名方式
            with open(f'./data/news_content/{self.source}_{self.feed_name}/{safe_link}.txt', 'r', encoding='utf-8') as f:  # 確保使用相同的命名方式
                news_content = f.read()
            try:
                ai_title, ai_summary = self.summarize_news(title, news_content)
                entries_df.loc[index, 'ai_title'] = ai_title  # 新增 ai_title
                entries_df.loc[index, 'ai_summary'] = ai_summary  # 新增 ai_summary
                print(entries_df.loc[index, 'ai_title'], '\n', entries_df.loc[index, 'ai_summary'], '\n\n')
            except Exception as e:
                print(f"Error: {e}")
                continue
        entries_df.to_csv(self.filename, index=False)
        self.save_to_csv(entries_df)

def load_rss_config() -> Dict:
    with open('config/rss_feed.yaml', 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

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
    rss_config = load_rss_config()

    parser = argparse.ArgumentParser(description="Process RSS feed URL and summarize news.")
    parser.add_argument('-s', '--source', choices=list(rss_config['news_sources'].keys()), help='Choose news source')
    parser.add_argument('-f', '--feed', help='Choose specific feed')
    parser.add_argument('-ff', '--force-fetch', action='store_true', help='Force fetch all news content')
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
        logger.error(f"Cannot find feed named {args.feed} in {args.source}")
        return

    rss_feed_url = feed['url']
    logger.info(f"Selected feed: {feed['name']}")

    ai_news = AINews(rss_feed_url, args.source, args.feed, force_fetch=args.force_fetch)
    ai_news.run()

if __name__ == "__main__":
    main()