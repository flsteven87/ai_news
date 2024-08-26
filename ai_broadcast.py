import os
import pandas as pd
from dotenv import load_dotenv
import openai
from pathlib import Path
import argparse
import yaml

class AIBroadcast:
    def __init__(self, source, feed_name, voice, force_regenerate=False):
        self.input_folder = f"./data/news_rewrite/{source}_{feed_name}"
        self.output_base_folder = "./data/news_broadcast"
        self.source = source
        self.feed_name = feed_name
        self.voice = voice
        self.force_regenerate = force_regenerate
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if openai.api_key is None:
            raise ValueError("OpenAI API key is not set in .env file.")

    def create_speech(self, text, output_file):
        response = openai.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text
        )
        response.stream_to_file(output_file)

    def run(self):
        output_folder = Path(self.output_base_folder) / f"{self.source}_{self.feed_name}"
        output_folder.mkdir(parents=True, exist_ok=True)

        print(f"輸入資料夾: {self.input_folder}")  # 調試輸出
        print(f"輸出資料夾: {output_folder}")  # 調試輸出

        # 讀取指定資料夾中的所有 txt 檔案
        for file in os.listdir(self.input_folder):
            if file.endswith(".txt"):  # 修改為讀取所有 .txt 檔案
                input_file = Path(self.input_folder) / file
                with open(input_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                url_safe_link = file[:-4]  # 保持檔名完全相同，去掉 ".txt"
                output_file = output_folder / f"{url_safe_link}_{self.voice}.mp3"
                
                print(f"處理檔案: {input_file}")  # 調試輸出
                if output_file.exists() and not self.force_regenerate:
                    print(f"音頻文件已存在，跳過: {output_file}")
                else:
                    self.create_speech(text, str(output_file))
                    print(f"已生成音頻: {output_file}")

def load_rss_config():
    with open('config/rss_feed.yaml', 'r') as file:
        return yaml.safe_load(file)

def select_source_and_feed(rss_config):
    sources = list(rss_config['news_sources'].keys())
    print("可用的新聞來源：")
    for i, source in enumerate(sources, 1):
        print(f"{i}. {source}")
    
    while True:
        try:
            source_index = int(input("請選擇新聞來源（輸入數字）: ")) - 1
            if 0 <= source_index < len(sources):
                source = sources[source_index]
                break
            else:
                print("無效的選擇，請重試。")
        except ValueError:
            print("請輸入有效的數字。")
    
    feeds = rss_config['news_sources'][source]['feeds']
    print(f"\n{source} 的用 feeds：")
    for i, feed in enumerate(feeds, 1):
        print(f"{i}. {feed['name']}")
    
    while True:
        try:
            feed_index = int(input("請選擇 feed（輸入數字）: ")) - 1
            if 0 <= feed_index < len(feeds):
                feed_name = feeds[feed_index]['name']
                break
            else:
                print("無效的選擇，請重試。")
        except ValueError:
            print("請輸入有效的數字。")
    
    return source, feed_name

def select_voice():
    voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
    print("\n可用的語音選項：")
    for i, voice in enumerate(voices, 1):
        print(f"{i}. {voice}")
    
    while True:
        try:
            voice_index = int(input("請選擇語音（輸入數字）: ")) - 1
            if 0 <= voice_index < len(voices):
                return voices[voice_index]
            else:
                print("無效的選擇，請重試。")
        except ValueError:
            print("請輸入有效的數字。")

def main():
    parser = argparse.ArgumentParser(description="生成新聞音頻播報")
    parser.add_argument('-s', '--source', help='新聞來')
    parser.add_argument('-f', '--feed', help='Feed 名稱')
    parser.add_argument('-v', '--voice', choices=['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'], help='OpenAI TTS 語音選項')
    parser.add_argument('--force', action='store_true', help='強制重新生成所有音頻')

    args = parser.parse_args()
    rss_config = load_rss_config()

    if not args.source or not args.feed:
        args.source, args.feed = select_source_and_feed(rss_config)
    
    if not args.voice:
        args.voice = select_voice()

    ai_broadcast = AIBroadcast(args.source, args.feed, args.voice, args.force)
    ai_broadcast.run()

if __name__ == "__main__":
    main()