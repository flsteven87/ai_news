import os
import requests
import pandas as pd
import feedparser
import argparse
from dotenv import load_dotenv
import openai
import json

class AINews:
    def __init__(self, rss_feed_url, filename):
        self.rss_feed_url = rss_feed_url
        self.filename = filename
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
    
    def parse_feed(self):
        feed = feedparser.parse(self.rss_feed_url)
        feed_data = {
            "feed_title": feed.feed.title,
            "feed_subtitle": feed.feed.subtitle if 'subtitle' in feed.feed else 'N/A',
            "feed_link": feed.feed.link,
            "feed_published": feed.feed.published if 'published' in feed.feed else 'N/A',
            "entries": [{
                "title": entry.title,
                "summary": entry.summary,
                "link": entry.link,
                "published": entry.published if 'published' in entry else 'No publish date'
            } for entry in feed.entries]
        }
        return feed_data
    
    def fetch_news_content(self, entries):
        for entry in entries:
            try:
                print(f"Crawling: {entry['title']} - Published: {entry['published']} - URL: {entry['link']}")
                response = requests.get(f"https://r.jina.ai/{entry['link']}", timeout=100)
                # 將新聞內容存儲到 news_content folder 內，並且以 link 作為檔名
                with open(f'./news_content/{entry["link"].replace("/", "_")}.txt', 'w') as f:
                    f.write(response.text)
            except requests.exceptions.RequestException as e:
                print(f"Failed to crawl content for: {entry['title']} - URL: {entry['link']} - Error: {e}")
    
    def summarize_news(self, title, news_content):

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位專業的記者，你的目標是以繁體中文總結一個英文報導，包含一個繁體中文標題及繁體中文總結，用戶透過你的總結能很明確的知道這篇新聞探討的議題及重點是什麼，來決定他們要不要閱讀完整的內文。"},
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
                    ai_title=function_args.get("title"),
                    ai_summary=function_args.get("summary")
        except Exception as e:
            print(f"Error: {e}")
            ai_title = ""
            ai_summary = ""

        return ai_title, ai_summary

    def save_to_csv(self, data_frame):
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
        data_frame.to_csv(self.filename, index=False)

    def run(self):
        feed_data = self.parse_feed()
        entries_df = pd.DataFrame(feed_data['entries'])
        entries_df.to_csv(self.filename, index=False)
        self.fetch_news_content(feed_data['entries'])
        for index, news in entries_df.iterrows():
            title = news['title']
            # 從 news_content folder 內讀取新聞內容
            with open(f'./news_content/{news["link"].replace("/", "_")}.txt', 'r') as f:
                news_content = f.read()
            try:
                ai_title, ai_summary = self.summarize_news(title, news_content)
                # ai_title 是tuple string, 需要先轉換成 tuple 後取第一個元素
                ai_title = ai_title[0] if ai_title else ""
                entries_df.loc[index, 'ai_title'] = ai_title
                entries_df.loc[index, 'ai_summary'] = ai_summary
                print(entries_df.loc[index, 'ai_title'], '\n', entries_df.loc[index, 'ai_summary'], '\n\n')
            except Exception as e:
                print(f"Error: {e}")
                continue
        entries_df.to_csv(self.filename, index=False)
        self.save_to_csv(entries_df)

def main():
    parser = argparse.ArgumentParser(description="Process an RSS feed URL and summarize news.")
    parser.add_argument('rss_feed_url', type=str, help='RSS Feed URL to process')
    parser.add_argument('--filename', type=str, default="./news/output.csv", help='Filename for the output CSV')
    args = parser.parse_args()
    
    ai_news = AINews(args.rss_feed_url, args.filename)
    ai_news.run()

if __name__ == "__main__":
    main()
