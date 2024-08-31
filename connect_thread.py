from threads_api.src.threads_api import ThreadsAPI
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def post():
    api = ThreadsAPI()
    await api.login(os.environ.get('USERNAME'), os.environ.get('PASSWORD'), cached_token_path=".token")
    result = await api.post(caption="Nvidia最新財報未達市場預期，導致其股價在盤後交易中下跌超過8%，並影響全球股市。亞洲市場的台積電和SK海力士等芯片股也受到拖累。Nvidia的收入雖然同比增長超過120%，但市場對其未來的高預期未能滿足，尤其是其新款Blackwell芯片的生產問題引發關注。這一結果使得市場對AI熱潮的可持續性產生疑慮，並影響了美國和歐洲股市期貨走勢。分析師指出，儘管短期內市場情緒受挫，但AI基礎設施的需求仍然強勁。")
    if result:
        print("Post has been successfully posted")
    else:
        print("Unable to post.")
    await api.close_gracefully()

async def main():
    await post()

# Run the main function
asyncio.run(main())