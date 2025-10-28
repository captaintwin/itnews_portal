from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.reporter import send_report
from utils.scheduler_poster import schedule_posts

def main():
    collect_all()
    extract_all_articles()
    selected = analyze_articles()
    send_report(selected)
    schedule_posts()

if __name__ == "__main__":
    main()
