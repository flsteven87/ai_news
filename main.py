from config.log_config import setup_logger
from pathlib import Path
import argparse
import yaml
from ai_news import AINews
from ai_chose import AIChose
from ai_rewrite import AIRewrite
from ai_broadcast import AIBroadcast

# logger = setup_logger(__name__)

def load_rss_config():
    with open('config/rss_feed.yaml', 'r') as file:
        return yaml.safe_load(file)

def parse_arguments():
    parser = argparse.ArgumentParser(description='AI新聞爬取和摘要工具')
    parser.add_argument('--rss_url', help='RSS feed URL')
    parser.add_argument('--source', help='新聞來源')
    parser.add_argument('--feed_name', help='Feed 名稱')
    parser.add_argument('--output', default='./data/news/{source}_{feed_name}.csv', help='輸出CSV檔案路徑')
    parser.add_argument('--chosen_output', default='./data/news_chosen/{source}_{feed_name}_chosen.csv', help='重要新聞輸出CSV檔案路徑')
    parser.add_argument('--num_chosen', type=int, default=5, help='選擇的重要新聞數量')
    return parser.parse_args()

def select_source_and_feed(rss_config):
    print("可用的新聞源:")
    for i, (key, source) in enumerate(rss_config['news_sources'].items(), 1):
        print(f"{i}. {source['name']}")
    print("請選擇新聞來源：")
    choice = input("輸入您的選擇")
    print(f"用戶選擇了: {choice}")
    try:
        index = int(choice) - 1
        if 0 <= index < len(rss_config['news_sources']):
            source_key = list(rss_config['news_sources'].keys())[index]
            source = rss_config['news_sources'][source_key]
            print(f"選擇了新聞源: {source['name']}")
            
            print("可用的 feeds:")
            for i, feed in enumerate(source['feeds'], 1):
                print(f"{i}. {feed['name']}")
            feed_choice = input("請輸入要使用的 feed 編號：")
            try:
                feed_index = int(feed_choice) - 1
                if 0 <= feed_index < len(source['feeds']):
                    rss_feed_url = source['feeds'][feed_index]['url']
                    feed_name = source['feeds'][feed_index]['name']
                    print(f"選擇了 feed: {feed_name}")
                    return source_key, feed_name, rss_feed_url
                else:
                    print("無效的選擇")
                    return None, None, None
            except ValueError:
                print("請輸入有效的數字")
                return None, None, None
        else:
            print("無效的選擇")
            return None, None, None
    except ValueError:
        print("請輸入有效的數字")
        return None, None, None

def main():
    args = parse_arguments()
    rss_config = load_rss_config()

    if not args.rss_url or not args.source or not args.feed_name:
        source, feed_name, rss_url = select_source_and_feed(rss_config)
        if not source or not feed_name or not rss_url:
            return
        args.source = source
        args.feed_name = feed_name
        args.rss_url = rss_url

    # 確保輸出目錄存在
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.chosen_output).parent.mkdir(parents=True, exist_ok=True)

    try:
        # 執行 AI 新聞爬取
        print("開始處理新聞數據")
        ai_news = AINews(args.rss_url, args.source, args.feed_name)
        ai_news.run()
        print("新聞數據處理完成")
        print(f"新聞爬取完成，結果保存在 {ai_news.filename}")

        # 執行 AI 新聞選擇
        print("開始選擇重要新聞")
        ai_chose = AIChose(args.source, args.feed_name, args.num_chosen)
        ai_chose.run()
        print("重要新聞選擇完成")
        print(f"重要新聞選擇完成，結果保存在 {ai_chose.output_filename}")

        # 執行 AI 重寫
        print("開始重寫重要新聞")
        ai_rewrite = AIRewrite()
        ai_rewrite.run(ai_chose.output_filename)
        print("重要新聞重寫完成")

        # 執行 AI 語音播報
        print("開始生成語音播報")
        voice = "nova"  # 這裡可以設置一個默認的語音選項，或從 args 中獲取
        ai_broadcast = AIBroadcast(args.source, args.feed_name, voice)
        ai_broadcast.run()
        print("語音播報生成完成")
        print(f"語音播報生成完成，結果保存在 news_broadcast/{args.source}_{args.feed_name} 目錄中")

    except Exception as e:
        print(f"執行過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()