import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from collections import Counter
import os

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 爬虫部分
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.hurun.net/zh-CN/Rank/HsRankDetails?pagetype=rich"
}

base_url = "https://www.hurun.net/zh-CN/Rank/HsRankDetailsList"


def fetch_all_data():
    all_data = []
    page = 1
    page_size = 100
    total = None

    with tqdm(desc="正在抓取数据") as pbar:
        while True:
            params = {
                "num": "ODBYW2BI",
                "page": page,
                "limit": page_size
            }

            try:
                response = requests.get(base_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if total is None:
                    total = data.get("total", 0)
                    if total == 0:
                        print("未获取到有效数据")
                        return []

                current_rows = data.get("rows", [])
                if not current_rows:
                    break

                all_data.extend(current_rows)
                pbar.update(len(current_rows))

                if len(all_data) >= total:
                    break

                page += 1

            except Exception as e:
                print(f"请求失败: {e}")
                break

    return all_data


def parse_data(raw_data):
    parsed = []
    for item in raw_data:
        persons = []
        for person in item.get("hs_Character", []):
            persons.append({
                "姓名": person.get("hs_Character_Fullname_Cn"),
                "性别": person.get("hs_Character_Gender_Lang"),
                "年龄": person.get("hs_Character_Age"),
                "照片": person.get("hs_Character_Photo", "")
            })

        parsed.append({
            "排名": item.get("hs_Rank_Rich_Ranking"),
            "财富(亿人民币)": item.get("hs_Rank_Rich_Wealth"),
            "财富(百万美元)": item.get("hs_Rank_Rich_Wealth_USD"),
            "排名变化": item.get("hs_Rank_Rich_Ranking_Change"),
            "公司中文名": item.get("hs_Rank_Rich_ComName_Cn"),
            "公司英文名": item.get("hs_Rank_Rich_ComName_En", ""),
            "行业中文": item.get("hs_Rank_Rich_Industry_Cn"),
            "行业英文": item.get("hs_Rank_Rich_Industry_En", ""),
            "家族关系": item.get("hs_Rank_Rich_Relations", ""),
            "成员信息": persons
        })
    return parsed


# 新增功能：行业分析
def industry_analysis(df):
    print("开始行业分析...")

    if '行业中文' not in df.columns:
        print("错误：数据中缺少'行业中文'列")
        return None

    # 行业富豪数量统计
    industry_count = df['行业中文'].value_counts().reset_index()
    industry_count.columns = ['行业', '富豪数量']

    # 行业财富总值统计
    industry_wealth = df.groupby('行业中文')['财富(亿人民币)'].sum().reset_index()
    industry_wealth.columns = ['行业', '总财富(亿人民币)']

    # 行业平均财富统计
    industry_avg = df.groupby('行业中文')['财富(亿人民币)'].mean().reset_index()
    industry_avg.columns = ['行业', '平均财富(亿人民币)']

    # 合并统计结果
    industry_stats = pd.merge(industry_count, industry_wealth, on='行业')
    industry_stats = pd.merge(industry_stats, industry_avg, on='行业')
    industry_stats = industry_stats.sort_values(by='富豪数量', ascending=False)

    # 保存行业统计数据
    industry_stats.to_excel("行业分析结果.xlsx", index=False)
    print("行业分析结果已保存到 '行业分析结果.xlsx'")

    # 行业可视化
    plt.figure(figsize=(15, 10))

    # 富豪数量TOP15行业
    plt.subplot(2, 2, 1)
    top15_industry = industry_stats.head(15)
    sns.barplot(x='富豪数量', y='行业', data=top15_industry,
                hue='行业', palette='viridis', legend=False, dodge=False)
    plt.title('各行业富豪数量TOP15')
    plt.xlabel('富豪数量')
    plt.ylabel('行业')

    # 总财富TOP15行业
    plt.subplot(2, 2, 2)
    top15_wealth = industry_stats.sort_values('总财富(亿人民币)', ascending=False).head(15)
    sns.barplot(x='总财富(亿人民币)', y='行业', data=top15_wealth,
                hue='行业', palette='magma', legend=False, dodge=False)
    plt.title('各行业总财富TOP15')
    plt.xlabel('总财富(亿人民币)')
    plt.ylabel('行业')

    # 平均财富TOP15行业
    plt.subplot(2, 2, 3)
    top15_avg = industry_stats.sort_values('平均财富(亿人民币)', ascending=False).head(15)
    sns.barplot(x='平均财富(亿人民币)', y='行业', data=top15_avg,
                hue='行业', palette='plasma', legend=False, dodge=False)
    plt.title('各行业平均财富TOP15')
    plt.xlabel('平均财富(亿人民币)')
    plt.ylabel('行业')

    # 富豪数量占比饼图
    plt.subplot(2, 2, 4)
    other_count = industry_stats['富豪数量'][15:].sum()
    pie_data = top15_industry[['行业', '富豪数量']].copy()
    pie_data.loc[len(pie_data)] = ['其他行业', other_count]
    plt.pie(pie_data['富豪数量'], labels=pie_data['行业'], autopct='%1.1f%%')
    plt.title('富豪行业分布')

    plt.tight_layout()
    plt.savefig('行业分析.png', dpi=300)
    plt.close()
    print("行业分析图表已保存为 '行业分析.png'")

    return industry_stats


def multi_dimensional_analysis(df):
    print("开始多维度分析...")

    # 1. 年龄分析 - 修复TypeError
    all_ages = []
    invalid_age_count = 0

    for persons in df['成员信息']:
        for person in persons:
            age = person.get('年龄')  # 使用get方法更安全

            # 健壮的类型检查和转换
            if age is None:
                invalid_age_count += 1
                continue

            try:
                # 尝试转换为整数（处理字符串"45"或数字45两种情况）
                age_int = int(float(age)) if str(age).strip() else None
                if age_int is not None and age_int > 0:
                    all_ages.append(age_int)
                else:
                    invalid_age_count += 1
            except (ValueError, TypeError, AttributeError):
                invalid_age_count += 1
                continue

    # 数据有效性检查
    if invalid_age_count > 0:
        print(f"警告：跳过 {invalid_age_count} 条无效年龄记录")

    if not all_ages:
        print("错误：没有有效的年龄数据可供分析")
        return None

    print(f"有效年龄记录数: {len(all_ages)}")



    # 年龄分布可视化
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    sns.histplot(all_ages, bins=20, kde=True, color='skyblue')
    plt.title('富豪年龄分布')
    plt.xlabel('年龄')
    plt.ylabel('人数')

    # 年龄分段统计
    age_bins = [0, 30, 40, 50, 60, 70, 100]
    age_labels = ['30岁以下', '31-40岁', '41-50岁', '51-60岁', '61-70岁', '71岁以上']
    age_groups = pd.cut(all_ages, bins=age_bins, labels=age_labels)
    age_count = age_groups.value_counts().sort_index()

    plt.subplot(1, 2, 2)
    age_count.plot(kind='bar', color='lightgreen')
    plt.title('富豪年龄段分布')
    plt.xlabel('年龄段')
    plt.ylabel('人数')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('年龄分析.png', dpi=300)
    plt.close()
    print("年龄分析图表已保存为 '年龄分析.png'")


    # 2. 性别分析
    genders = []
    for persons in df['成员信息']:
        for person in persons:
            if person['性别']:
                genders.append(person['性别'])

    gender_count = pd.Series(genders).value_counts()

    plt.figure(figsize=(10, 6))
    plt.pie(gender_count, labels=gender_count.index, autopct='%1.1f%%',
            colors=['lightcoral', 'lightblue'], startangle=90)
    plt.title('富豪性别分布')
    plt.savefig('性别分析.png', dpi=300)
    plt.close()
    print("性别分析图表已保存为 '性别分析.png'")

    # 3. 财富与年龄关系
    # 创建个人级别的数据集
    person_data = []
    for _, row in df.iterrows():
        for person in row['成员信息']:
            if person['年龄']:
                try:
                    age = int(person['年龄'])
                    if age > 0:
                        person_data.append({
                            '年龄': age,  # 存储转换后的整数
                            '财富(亿人民币)': row['财富(亿人民币)'],
                            '行业': row['行业中文'] if '行业中文' in row else '未知'
                        })
                except (ValueError, TypeError):
                    pass  # 忽略转换失败的情况

    person_df = pd.DataFrame(person_data)

    # 财富与年龄散点图
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='年龄', y='财富(亿人民币)', data=person_df, alpha=0.6)
    plt.title('财富与年龄关系')
    plt.savefig('财富年龄关系.png', dpi=300)
    plt.close()
    print("财富与年龄关系图表已保存为 '财富年龄关系.png'")

    # 4. 行业-年龄热力图
    # 选择富豪数量最多的15个行业
    if '行业中文' in df.columns:
        top_industries = df['行业中文'].value_counts().head(15).index
        filtered_df = person_df[person_df['行业'].isin(top_industries)]

        # 创建热力图数据
        heatmap_data = filtered_df.pivot_table(index='行业', columns=pd.cut(filtered_df['年龄'], bins=10),
                                               values='财富(亿人民币)', aggfunc='count', fill_value=0)

        plt.figure(figsize=(15, 10))
        sns.heatmap(heatmap_data, cmap='YlGnBu', annot=True, fmt='d')
        plt.title('不同行业富豪年龄分布热力图')
        plt.xlabel('年龄段')
        plt.ylabel('行业')
        plt.savefig('行业年龄热力图.png', dpi=300)
        plt.close()
        print("行业年龄热力图已保存为 '行业年龄热力图.png'")

    # 5. 财富分段统计
    wealth_bins = [0, 100, 200, 500, 1000, 5000]
    wealth_labels = ['<100亿', '100-200亿', '200-500亿', '500-1000亿', '>1000亿']
    df['财富分段'] = pd.cut(df['财富(亿人民币)'], bins=wealth_bins, labels=wealth_labels)
    wealth_segment = df['财富分段'].value_counts().sort_index()

    plt.figure(figsize=(10, 6))
    wealth_segment.plot(kind='bar', color='goldenrod')
    plt.title('财富分布情况')
    plt.xlabel('财富区间(亿人民币)')
    plt.ylabel('人数')
    plt.savefig('财富分布.png', dpi=300)
    plt.close()
    print("财富分布图表已保存为 '财富分布.png'")

    # 6. 出生地分析（由于数据中无出生地信息，这里使用公司所在地代替）
    if '公司中文名' in df.columns:
        # 提取公司所在地（假设公司名中包含城市信息）
        df['城市'] = df['公司中文名'].apply(
            lambda x: x.split('(')[-1].split(')')[0] if '(' in x and ')' in x else '未知')

        # 统计各城市富豪数量
        city_count = df['城市'].value_counts().head(15)

        plt.figure(figsize=(12, 8))
        city_count.plot(kind='bar', color='purple')
        plt.title('富豪公司所在地分布TOP15')
        plt.xlabel('城市')
        plt.ylabel('富豪数量')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('城市分布.png', dpi=300)
        plt.close()
        print("城市分布图表已保存为 '城市分布.png'")

    return {
        'age_data': all_ages,
        'gender_data': genders,
        'person_df': person_df
    }


if __name__ == "__main__":
    print("开始抓取胡润百富榜数据...")
    raw_data = fetch_all_data()

    if raw_data:
        print(f"共获取到{len(raw_data)}条数据，正在解析...")
        parsed_data = parse_data(raw_data)
        df = pd.DataFrame(parsed_data)

        # 创建输出目录
        os.makedirs('output', exist_ok=True)

        # 保存原始数据
        output_file = "output/2024胡润百富榜.xlsx"
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='原始数据')
        print(f"原始数据已保存到 {output_file}")

        # 行业分析
        industry_stats = industry_analysis(df)

        # 多维度分析
        analysis_results = multi_dimensional_analysis(df)

        # 将分析结果保存到Excel
        with pd.ExcelWriter("output/胡润百富榜分析结果.xlsx") as writer:
            if industry_stats is not None:
                industry_stats.to_excel(writer, sheet_name='行业分析', index=False)

            # 年龄分布
            age_df = pd.DataFrame(analysis_results['age_data'], columns=['年龄'])
            age_df.to_excel(writer, sheet_name='年龄分布', index=False)

            # 性别分布
            gender_df = pd.Series(analysis_results['gender_data']).value_counts().reset_index()
            gender_df.columns = ['性别', '人数']
            gender_df.to_excel(writer, sheet_name='性别分布', index=False)

            # 个人数据
            analysis_results['person_df'].to_excel(writer, sheet_name='个人数据', index=False)

        print("分析结果已保存到 'output/胡润百富榜分析结果.xlsx'")
        print("所有分析完成！")
    else:
        print("未能获取有效数据")