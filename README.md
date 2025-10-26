IT News Portal Bot

📰 Automated IT News Aggregator with Telegram Posting

Features

Parses RSS feeds from trusted IT sources (TechCrunch, The Verge, Wired, and others)

Extracts the main image from each article page

Filters out spam and outdated news

Automatically posts to a Telegram channel

Installation
git clone https://github.com/yourname/itnews_portal.git
cd itnews_portal
pip install -r requirements.txt

Configuration

Create a .env file in the project root and add your credentials:

TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT=your_chat_id

Run Locally
python main.py

🚀 Publish to GitHub

Create a new repository on GitHub (for example, itnews_portal).

Initialize your project locally:

git init
git add .
git commit -m "Initial commit"


Link the local project to GitHub and push it:

git remote add origin https://github.com/<your_username>/itnews_portal.git
git branch -M main
git push -u origin main


Would you like me to add the Deploy to Heroku section next (ready-to-copy commands and explanation)?