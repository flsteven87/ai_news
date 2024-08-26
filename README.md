# AI News Summarizer and Broadcaster

AI News Summarizer and Broadcaster is a Python-based tool that automatically fetches, summarizes, and broadcasts news articles. It uses advanced AI technologies to process RSS feeds, generate summaries in Traditional Chinese, and create audio broadcasts of selected news items.

## Features

- Automatic news fetching from specified RSS feeds
- AI-powered summarization of news articles in Traditional Chinese
- Selection of important news items based on relevance and impact
- News grouping and tagging for efficient categorization
- Text-to-speech conversion for audio broadcasting
- Web interface for easy viewing of summarized news

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-news-summarizer.git
   cd ai_news
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Configure RSS feeds in `src/config/rss_feed.yaml`.

## Usage

1. Run the main script to fetch and process news:
   ```
   python main.py
   ```

2. To select and summarize important news:
   ```
   python -m src.ai_chose
   ```

3. To generate audio broadcasts:
   ```
   python -m src.ai_broadcast
   ```

4. To view the summarized news through a web interface:
   ```
   streamlit run app.py
   ```

## Project Structure

- `src/`: Contains the main source code
  - `ai_news.py`: Handles news fetching and initial processing
  - `ai_chose.py`: Selects important news items
  - `ai_rewrite.py`: Rewrites news summaries
  - `ai_broadcast.py`: Generates audio broadcasts
- `data/`: Stores processed news data
- `prompt/`: Contains prompt templates for AI processing
- `app.py`: Streamlit web application for viewing news
- `poster.py`: Scheduled news processing and posting

## Dependencies

Key dependencies include:
- OpenAI
- Streamlit
- Pandas
- Feedparser
- Google Cloud Text-to-Speech

For a full list, see `requirements.txt`.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgments

- OpenAI for providing the GPT models used in summarization
- Google Cloud for the Text-to-Speech API
- All contributors and maintainers of the open-source libraries used in this project