import feedparser
import pandas as pd

def parse_feed(feed_url):
    # Parse the RSS feed from the provided URL
    feed = feedparser.parse(feed_url)
    return feed

def extract_feed_data(feed):
    # Extract and structure the feed data
    feed_data = {
        "feed_title": feed.feed.title,
        "feed_subtitle": feed.feed.subtitle,
        "feed_link": feed.feed.link,
        "feed_published": feed.feed.published if 'published' in feed.feed else 'N/A',
        "entries": [{
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link,
            "published": entry.published
        } for entry in feed.entries]
    }
    return feed_data

def convert_to_dataframe(entries):
    # Convert the entries to a DataFrame
    entries_df = pd.DataFrame(entries)
    return entries_df

def main():
    feed_url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    feed = parse_feed(feed_url)
    feed_data = extract_feed_data(feed)
    entries_df = convert_to_dataframe(feed_data["entries"])
    entries_df.to_csv("./news/bbc.csv", index=False)

if __name__ == "__main__":
    main()