# Supporting libraries
import os
from dotenv import load_dotenv
import pandas as pd
import json
# OpenAI
import openai

class NewsSummarizer:
  def __init__(self):
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

  def read_news_content(self, filename):
    with open(f'./news_content/{filename}.txt', 'r') as f:
      return f.read()

  def summarize_news(self, title, news_content):
    response = self.client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
      {"role": "system", "content": "你是一位專業的記者，你的目標是以繁體中文總結一個英文報導，包含一個繁體中文標題及繁體中文總結，用戶透過你的總結能很明確的知道這篇新聞探討的議題及重點是什麼，來決定他們要不要閱讀完整的內文。"},
      {"role": "user", "content": f"title: {title}, content:{news_content}"},
      ],
      tools=self.tools,
      tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            # function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            ai_title=function_args.get("title"),
            ai_summary=function_args.get("summary")

    return ai_title, ai_summary

  def run(self):
    df = pd.read_csv('./news/bbc.csv')

    for index, news in df.iterrows():
      filename = news['link'].split('/')[-1]
      title = news['title']
      news_content = self.read_news_content(filename)
      ai_title, ai_summary = self.summarize_news(title, news_content)
      df.loc[index, 'ai_title'] = ai_title
      df.loc[index, 'ai_summary'] = ai_summary
      print(df.loc[index, 'ai_title'], '\n', df.loc[index, 'ai_summary'], '\n\n')


    df.to_csv('./news/bbc_summary.csv', index=False)

if __name__ == "__main__":
  summarizer = NewsSummarizer()
  summarizer.run()
