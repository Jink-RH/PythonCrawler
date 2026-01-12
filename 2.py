

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import requests
from bs4 import BeautifulSoup
import time
import os
import random
from tqdm import tqdm
from datetime import datetime
import re
import chardet

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class DalianWeatherAnalyzer:
    def __init__(self):
        self.data_file = 'dalian_weather_2022_to_2024.csv'
        self.weather_data = None

    def decode_response(self, response):
        """自动检测并解码响应内容"""
        encoding = chardet.detect(response.content)['encoding']
        for enc in [encoding, 'gbk', 'gb18030', 'utf-8']:
            try:
                if enc:
                    return response.content.decode(enc)
            except:
                continue
        return response.text

    def get_daily_weather_data(self, row):
        """从单行表格数据中提取天气信息 - 对应题目(1)"""
        cols = row.find_all('td')
        if len(cols) < 4:
            return None

        try:
            # 提取日期
            date_link = cols[0].find('a')
            if date_link and 'href' in date_link.attrs:
                date_str = re.search(r'/(\d{8})\.html', date_link['href']).group(1)
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                date = date_obj.strftime('%Y-%m-%d')
            else:
                return None

            # 提取天气状况（白天和夜晚）
            weather_col = cols[1].get_text(' ', strip=True)
            weather = weather_col.split('/')
            day_weather = weather[0].strip() if len(weather) > 0 else ''
            night_weather = weather[1].strip() if len(weather) > 1 else ''

            # 提取温度（最高和最低）
            temp_col = cols[2].get_text(' ', strip=True)
            temp = temp_col.split('/')
            high_temp = re.sub(r'[^0-9\-]', '', temp[0]) if len(temp) > 0 else ''
            low_temp = re.sub(r'[^0-9\-]', '', temp[1]) if len(temp) > 1 else ''

            # 提取风力（白天和夜晚）
            wind_col = cols[3].get_text(' ', strip=True)
            wind = wind_col.split('/')
            day_wind = wind[0].strip() if len(wind) > 0 else ''
            night_wind = wind[1].strip() if len(wind) > 1 else ''

            return {
                '日期': date,
                '白天天气': day_weather,
                '夜晚天气': night_weather,
                '最高温度': high_temp,
                '最低温度': low_temp,
                '白天风力': day_wind,
                '夜晚风力': night_wind
            }
        except Exception as e:
            print(f"处理行数据时出错: {str(e)}")
            return None

    def get_dalian_monthly_weather(self, year, month):
        """爬取大连市指定年月的历史天气数据 - 对应题目(1)"""
        url = f"https://www.tianqihoubao.com/lishi/dalian/month/{year}{month:02d}.html"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tianqihoubao.com/lishi/'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = None
            decoded_content = self.decode_response(response)
            soup = BeautifulSoup(decoded_content, 'html.parser')

            table = soup.find('table', class_='b') or soup.find('table', class_='weather-table') or soup.find('table')

            if not table:
                print(f"未找到{year}年{month}月天气数据表格")
                return None

            rows = table.find_all('tr')
            monthly_data = []

            for row in rows:
                if row.find('th') or not row.find('td'):
                    continue

                daily_data = self.get_daily_weather_data(row)
                if daily_data:
                    monthly_data.append(daily_data)

            if not monthly_data:
                print(f"{year}年{month}月无有效数据")
                return None

            df = pd.DataFrame(monthly_data)
            df['年份'] = year
            df['月份'] = month

            df['最高温度'] = pd.to_numeric(df['最高温度'], errors='coerce')
            df['最低温度'] = pd.to_numeric(df['最低温度'], errors='coerce')

            df = df[['日期', '年份', '月份', '白天天气', '夜晚天气',
                     '最高温度', '最低温度', '白天风力', '夜晚风力']]

            return df

        except Exception as e:
            print(f"获取{year}年{month}月数据失败: {str(e)}")
            return None

    def crawl_dalian_weather(self, start_year=2022, end_year=2024):
        """爬取指定年份范围的大连天气数据 - 对应题目(1)"""
        all_data = []
        failed_months = []

        for year in tqdm(range(start_year, end_year + 1), desc='年份进度'):
            for month in tqdm(range(1, 13), desc=f'{year}年月份进度', leave=False):
                try:
                    monthly_data = self.get_dalian_monthly_weather(year, month)
                    if monthly_data is not None:
                        all_data.append(monthly_data)
                    else:
                        failed_months.append(f"{year}-{month:02d}")

                    delay = random.uniform(2, 5)
                    time.sleep(delay)

                except Exception as e:
                    print(f"处理{year}年{month}月数据时发生异常: {str(e)}")
                    failed_months.append(f"{year}-{month:02d}")
                    time.sleep(10)

        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df.to_csv(self.data_file, index=False, encoding='utf_8_sig')
            print(f"\n数据已保存为 {self.data_file}")
            self.weather_data = final_df
            return final_df
        else:
            print("未获取到任何有效数据")
            return None

    def load_data(self):
        """加载天气数据"""
        if os.path.exists(self.data_file):
            self.weather_data = pd.read_csv(self.data_file, encoding='utf_8_sig')
            return True
        else:
            print(f"文件 {self.data_file} 不存在，请先爬取数据")
            return False

    def plot_monthly_avg_temp(self):
        """绘制近三年月平均气温变化图 - 对应题目(2)"""
        if not self.load_data():
            return

        # 计算每月平均最高温和最低温
        monthly_avg = self.weather_data.groupby('月份').agg({
            '最高温度': 'mean',
            '最低温度': 'mean'
        }).reset_index()

        plt.figure(figsize=(12, 6))
        plt.plot(monthly_avg['月份'], monthly_avg['最高温度'], 'r-o', label='平均最高温度')
        plt.plot(monthly_avg['月份'], monthly_avg['最低温度'], 'b-o', label='平均最低温度')

        plt.title('大连市近三年月平均气温变化(2022-2024)', fontsize=16)
        plt.xlabel('月份', fontsize=14)
        plt.ylabel('温度(℃)', fontsize=14)
        plt.xticks(range(1, 13))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)

        for x, y1, y2 in zip(monthly_avg['月份'], monthly_avg['最高温度'], monthly_avg['最低温度']):
            plt.text(x, y1 + 0.5, f'{y1:.1f}℃', ha='center', va='bottom', fontsize=10)
            plt.text(x, y2 - 0.5, f'{y2:.1f}℃', ha='center', va='top', fontsize=10)

        plt.tight_layout()
        plt.savefig('月平均气温变化.png', dpi=300)
        plt.show()

    def plot_wind_distribution(self):
        """绘制近三年风力情况分布图 - 对应题目(3)"""
        if not self.load_data():
            return

        # 提取风力等级
        self.weather_data['风力等级'] = self.weather_data['白天风力'].str.extract(r'(\d-\d)级')[0]

        # 统计各风力等级出现天数
        wind_counts = self.weather_data['风力等级'].value_counts().sort_index()

        # 绘制柱状图
        plt.figure(figsize=(12, 6))
        wind_counts.plot(kind='bar', color='#66b3ff', edgecolor='black')

        plt.title('大连市近三年风力等级分布(2022-2024)', fontsize=16)
        plt.xlabel('风力等级', fontsize=14)
        plt.ylabel('出现天数', fontsize=14)
        plt.xticks(rotation=0)
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)

        for i, v in enumerate(wind_counts):
            plt.text(i, v + 3, str(v), ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        plt.savefig('风力等级分布.png', dpi=300)
        plt.show()

        # 绘制饼图
        plt.figure(figsize=(10, 10))
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
        patches, texts, autotexts = plt.pie(
            wind_counts,
            labels=wind_counts.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 12}
        )

        plt.title('大连市近三年风力等级占比(2022-2024)', fontsize=16)
        plt.setp(autotexts, size=12, weight="bold")
        plt.tight_layout()
        plt.savefig('风力等级占比.png', dpi=300)
        plt.show()

    def plot_weather_distribution(self):
        """绘制近三年天气状况分布图 - 对应题目(4)"""
        if not self.load_data():
            return

        # 合并白天和夜晚天气
        all_weather = pd.concat([self.weather_data['白天天气'], self.weather_data['夜晚天气']])

        # 统计各类天气出现次数
        weather_counts = all_weather.value_counts().head(8)

        # 绘制柱状图
        plt.figure(figsize=(12, 6))
        weather_counts.plot(kind='bar', color='#99ff99', edgecolor='black')

        plt.title('大连市近三年天气状况分布(2022-2024)', fontsize=16)
        plt.xlabel('天气类型', fontsize=14)
        plt.ylabel('出现天数', fontsize=14)
        plt.xticks(rotation=30)
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)

        for i, v in enumerate(weather_counts):
            plt.text(i, v + 5, str(v), ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        plt.savefig('天气状况分布.png', dpi=300)
        plt.show()

    def predict_temperature(self):
        """训练温度预测模型并预测2025年温度 - 对应题目(5)"""
        if not self.load_data():
            return

        # 计算每月平均最高温度
        monthly_avg = self.weather_data.groupby('月份')['最高温度'].mean().reset_index()

        # 准备训练数据
        X = monthly_avg['月份'].values.reshape(-1, 1)
        y = monthly_avg['最高温度'].values

        # 训练多项式回归模型
        poly = PolynomialFeatures(degree=3)
        X_poly = poly.fit_transform(X)

        model = LinearRegression()
        model.fit(X_poly, y)

        # 预测2025年各月温度
        months_2025 = np.array(range(1, 13)).reshape(-1, 1)
        X_2025_poly = poly.transform(months_2025)
        predictions = model.predict(X_2025_poly)

        # 模拟2025年数据（实际应用中应爬取真实数据）
        def simulate_2025_data():
            print("正在模拟2025年数据（实际应用中请替换为真实爬取）")
            np.random.seed(42)
            return predictions[:6] + np.random.normal(0, 1, 6)

        actual_2025 = simulate_2025_data()

        # 绘制预测结果对比图
        plt.figure(figsize=(12, 6))

        # 绘制历史平均温度
        plt.plot(monthly_avg['月份'], monthly_avg['最高温度'], 'b-o',
                 label='历史平均(2022-2024)', linewidth=2)

        # 绘制预测温度
        plt.plot(months_2025, predictions, 'g--o',
                 label='2025年预测', linewidth=2)

        # 绘制2025年"实际"温度（1-6月）
        plt.plot(range(1, 7), actual_2025, 'r-o',
                 label='2025年模拟数据', linewidth=2)

        plt.title('大连市月平均最高温度预测对比(2022-2025)', fontsize=16)
        plt.xlabel('月份', fontsize=14)
        plt.ylabel('温度(℃)', fontsize=14)
        plt.xticks(range(1, 13))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)

        # 添加数据标签
        for x, y in zip(monthly_avg['月份'], monthly_avg['最高温度']):
            plt.text(x, y + 0.5, f'{y:.1f}℃', ha='center', va='bottom', fontsize=10)

        for x, y in zip(months_2025.flatten(), predictions):
            plt.text(x, y - 0.5, f'{y:.1f}℃', ha='center', va='top', fontsize=10)

        for x, y in zip(range(1, 7), actual_2025):
            plt.text(x, y + 0.5, f'{y:.1f}℃', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        plt.savefig('temperature_prediction_comparison.png', dpi=300)
        plt.show()

    def run_all_analysis(self):
        """运行所有分析和可视化"""
        if not os.path.exists(self.data_file):
            print("未找到天气数据文件，开始爬取数据...")
            self.crawl_dalian_weather(2022, 2024)

        print("\n正在执行题目(2): 绘制月平均气温变化图")
        self.plot_monthly_avg_temp()

        print("\n正在执行题目(3): 绘制风力情况分布图")
        self.plot_wind_distribution()

        print("\n正在执行题目(4): 绘制天气状况分布图")
        self.plot_weather_distribution()

        print("\n正在执行题目(5): 训练温度预测模型并预测2025年温度")
        self.predict_temperature()


if __name__ == '__main__':
    print("大连市天气数据分析与预测系统启动")
    print("对应题目要求：")
    print("(1) 爬取天气数据 (2) 月平均气温变化图 (3) 风力分布图 (4) 天气状况分布图 (5) 温度预测")

    analyzer = DalianWeatherAnalyzer()
    analyzer.run_all_analysis()

    print("\n所有分析已完成！")