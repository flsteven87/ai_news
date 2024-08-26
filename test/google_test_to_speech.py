import os
import pandas as pd
from dotenv import load_dotenv
from google.cloud import texttospeech

# 加載 .env 文件中的環境變數
load_dotenv()

# 取得 Google Cloud 憑證路徑
google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# 確認環境變數是否正確加載
if google_credentials_path is None:
    raise ValueError("Google Cloud credentials path is not set in .env file.")

# 從 CSV 文件讀取 ai_rewritten 欄位的第一行內容
csv_file_path = 'data/news_chosen/the_guardian_Latest.csv'
df = pd.read_csv(csv_file_path)

if 'ai_rewritten' not in df.columns:
    raise ValueError("The column 'ai_rewritten' does not exist in the CSV file.")

first_ai_rewritten = df.loc[0, 'ai_rewritten']

# 創建 Text-to-Speech 客戶端
client = texttospeech.TextToSpeechClient()

# 使用 WaveNet 語音模型
voice = texttospeech.VoiceSelectionParams(
    language_code="zh-TW",  # 語言代碼，表示中文（台灣）
    name="cmn-TW-Wavenet-A",  # WaveNet 語音模型，中文（台灣）WaveNet B
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE  # 語音性別設置為女性
)

# 設定音頻配置，調整語速和音調
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,  # 音頻格式設置為 MP3
    pitch=0.5,  # 輕微調高音調
    speaking_rate=1 g
)

# 呼叫 API 生成語音
response = client.synthesize_speech(
    input=texttospeech.SynthesisInput(text=first_ai_rewritten),
    voice=voice,
    audio_config=audio_config
)

# 將生成的語音內容寫入 MP3 文件
output_audio_file = 'output.mp3'
with open(output_audio_file, 'wb') as out:
    out.write(response.audio_content)
    print(f"音頻已生成並保存到 {output_audio_file}")
