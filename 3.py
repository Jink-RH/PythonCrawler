import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re
from collections import Counter
import random
from time import sleep

# ===== 本地停用词列表 =====
stop_words = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
    'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she',
    'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
    'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
    'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an',
    'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of',
    'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
    'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
    'can', 'will', 'just', 'don', 'should', 'now', 'via', 'using', 'based'
}


# ================== 任务1：数据爬取 ==================
def get_dblp_url(conference, year):
    """生成DBLP会议URL（处理ICML小写问题）"""
    if conference == "ICML":
        return f"https://dblp.org/db/conf/icml/icml{year}.html"
    else:
        return f"https://dblp.org/db/conf/{conference.lower()}/{conference.lower()}{year}.html"


def scrape_dblp(conference, year):
    """爬取单年会议论文数据"""
    url = get_dblp_url(conference, year)
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for entry in soup.find_all('li', class_='entry inproceedings'):
            title = entry.find('span', class_='title').text.strip()
            authors = [a.text.strip() for a in entry.find_all('span', itemprop='author')]
            link_tag = entry.find('a', itemprop='url')
            papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "year": year,
                "conference": conference,
                "url": link_tag['href'] if link_tag else "N/A"
            })

        sleep(random.uniform(1, 3))
        return papers

    except Exception as e:
        print(f"Error scraping {conference} {year}: {e}")
        return []


def scrape_all_conferences():
    """爬取所有会议数据"""
    conferences = {
        "CVPR": list(range(2020, 2025)),
        "ICML": list(range(2020, 2025)),
        "KDD": list(range(2020, 2025))
    }

    all_papers = []
    for conf, years in conferences.items():
        print(f"Scraping {conf}...")
        for year in years:
            papers = scrape_dblp(conf, year)
            all_papers.extend(papers)
            print(f"  - {year}: {len(papers)} papers")

    df = pd.DataFrame(all_papers)
    df.to_excel("conference_papers_2020-2024.xlsx", index=False)
    return df


# ===== 任务2：论文数量趋势图 =====
def plot_paper_trends(df):
    """绘制各会议论文数量年度趋势"""
    trend_data = df.groupby(['conference', 'year']).size().unstack()
    trend_data.plot(kind='line', marker='o', figsize=(10, 6))
    plt.title('Conference Paper Trends (2020-2024)')
    plt.ylabel('Number of Papers')
    plt.grid(True)
    plt.savefig('paper_trends.png')
    plt.show()


# ===== 任务3：关键词分析 =====
def preprocess_title(title):
    """标题预处理：提取有效关键词"""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
    return [w for w in words if w not in stop_words]


def generate_wordcloud(df, conference):
    """生成会议年度关键词词云"""
    for year in sorted(df['year'].unique()):
        titles = ' '.join(df[(df['conference'] == conference) & (df['year'] == year)]['title'])
        words = preprocess_title(titles)
        word_freq = Counter(words).most_common(50)

        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white'
        ).generate_from_frequencies(dict(word_freq))

        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.title(f'{conference} {year} - Top Keywords')
        plt.axis('off')
        plt.savefig(f'{conference}_wordcloud_{year}.png', bbox_inches='tight')
        plt.close()


# ===== 任务4：论文数量预测 =====
def predict_paper_count(df):
    """预测下一届会议论文数量"""
    from sklearn.linear_model import LinearRegression
    import numpy as np

    predictions = {}
    for conf in df['conference'].unique():
        conf_data = df[df['conference'] == conf]
        year_counts = conf_data.groupby('year').size()

        if len(year_counts) < 2:
            continue

        X = np.array(year_counts.index).reshape(-1, 1)
        y = year_counts.values
        model = LinearRegression().fit(X, y)
        next_year = max(year_counts.index) + 1
        pred = int(model.predict([[next_year]])[0])

        predictions[conf] = {
            "next_year": next_year,
            "predicted_count": pred,
            "growth_rate": f"{(pred - year_counts.iloc[-1]) / year_counts.iloc[-1] * 100:.1f}%"
        }

    return pd.DataFrame(predictions).T


# ===== 主程序 =====
if __name__ == "__main__":
    # 先尝试读取已有数据，如果没有则爬取
    try:
        df = pd.read_excel("conference_papers_2020-2024.xlsx")
        print("检测到已有数据文件，直接加载...")
    except FileNotFoundError:
        print("未找到数据文件，开始爬取数据...")
        df = scrape_all_conferences()
        print("数据爬取完成！")

    # 执行分析任务
    print("\n开始分析任务...")
    plot_paper_trends(df)  # 任务2
    generate_wordcloud(df, "CVPR")  # 任务3（示例分析CVPR）

    # 任务4：预测
    predictions = predict_paper_count(df)
    print("\n论文数量预测结果:")
    print(predictions)