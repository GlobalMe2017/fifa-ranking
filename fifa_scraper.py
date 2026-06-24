#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIFA国家队排名历史数据抓取工具 v4
增加：自动重试机制 + 失败国家单独重试功能

# 完整抓取
python fifa_scraper.py

# 重试失败的国家
python fifa_scraper.py --retry
"""

import json
import requests
import time
import csv
import os
import sys
from datetime import datetime

# ===== 配置区域 =====
INPUT_FILE = "fifa_api_success.txt"
OUTPUT_DIR = "fifa_rankings_output"
REQUEST_DELAY = 2  # 每次请求间隔2秒
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAYS = [10, 30, 60]  # 重试等待时间（秒）
BASE_URL = "https://inside.fifa.com/api/rankings/by-country"

# ===== 完整的浏览器请求头 =====
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.fifa.com/fifa-world-ranking/",
    "Origin": "https://www.fifa.com",
    "Sec-Ch-Ua": '"Chromium";v="137", "Not=A?Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Connection": "keep-alive",
    "Dnt": "1",
}

session = requests.Session()
session.headers.update(HEADERS)


def check_file_exists(filepath):
    """检查文件是否存在"""
    if not os.path.exists(filepath):
        print(f"❌ 错误: 找不到文件 '{filepath}'")
        print(f"   当前工作目录: {os.getcwd()}")
        return False
    return True


def parse_country_codes(json_file_path):
    """从FIFA API成功响应JSON中解析所有国家队的3字母短码"""
    print(f"📖 正在读取文件: {json_file_path}")

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        data = json.loads(content)
        print(f"✅ JSON解析成功")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return []

    results = data.get('Results', [])
    if not results:
        print("❌ 未找到 Results 字段或 Results 为空")
        return []

    country_codes = []
    for item in results:
        country_code = item.get('IdCountry')
        if country_code:
            country_codes.append(country_code)

    country_codes = sorted(list(set(country_codes)))

    print(f"📋 共解析到 {len(country_codes)} 个国家队的短码")
    print(f"   示例: {country_codes[:10]}")

    return country_codes


def fetch_country_ranking_history(country_code, retry_count=0):
    """
    请求单个国家队的FIFA排名历史数据
    支持重试机制
    """
    params = {
        "gender": 1,
        "countryCode": country_code,
        "locale": "en"
    }

    try:
        response = session.get(BASE_URL, params=params, timeout=30)

        if response.status_code == 403:
            return None, "403 Forbidden"
        elif response.status_code == 429:
            return None, "429 Too Many Requests"
        elif response.status_code != 200:
            return None, f"HTTP {response.status_code}"

        data = response.json()
        rankings = data.get('rankings', [])

        if not rankings:
            return None, "无排名数据"

        return rankings, "成功"

    except requests.exceptions.Timeout:
        return None, "请求超时"
    except requests.exceptions.ConnectionError:
        return None, "连接错误"
    except json.JSONDecodeError as e:
        return None, f"JSON解析失败: {str(e)}"
    except Exception as e:
        return None, f"未知错误: {str(e)}"


def fetch_with_retry(country_code):
    """
    带重试机制的请求
    返回: (rankings, error_message, attempts)
    """
    for attempt in range(MAX_RETRIES):
        rankings, message = fetch_country_ranking_history(country_code, attempt)

        if rankings:
            return rankings, None, attempt + 1

        # 如果不是最后一次尝试，等待后重试
        if attempt < MAX_RETRIES - 1:
            wait_time = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"   ⏳ 第{attempt + 1}次失败 ({message})，等待{wait_time}秒后重试...")
            time.sleep(wait_time)
        else:
            return None, message, attempt + 1

    return None, "所有重试均失败", MAX_RETRIES


def fetch_single_country(country_code):
    """
    单独请求一个国家（用于命令行重试）
    返回: (success, message)
    """
    print(f"\n🔍 正在单独请求 {country_code}...")
    rankings, message = fetch_country_ranking_history(country_code)

    if rankings:
        rows = rankings_to_csv_rows(rankings, country_code)
        save_country_csv(country_code, rows)
        print(f"✅ {country_code}: 成功获取 {len(rankings)} 条记录")
        return True, "成功"
    else:
        print(f"❌ {country_code}: {message}")
        return False, message


def rankings_to_csv_rows(rankings, country_code):
    """将排名数据转换为CSV行数据"""
    rows = []
    for entry in rankings:
        team_names = entry.get('TeamName', [])
        country_name = team_names[0].get('Description', '') if team_names else ''

        pub_date = entry.get('PubDate', '')
        if pub_date and len(pub_date) >= 10:
            pub_date = pub_date[:10]

        total_points = entry.get('DecimalTotalPoints') or entry.get('TotalPoints') or ''
        prev_points = entry.get('DecimalPrevPoints') or entry.get('PrevPoints') or ''

        row = {
            'CountryCode': country_code,
            'CountryName': country_name,
            'Rank': entry.get('Rank', ''),
            'PrevRank': entry.get('PrevRank', ''),
            'TotalPoints': total_points,
            'PrevPoints': prev_points,
            'Matches': entry.get('Matches', ''),
            'RankingMovement': entry.get('RankingMovement', ''),
            'Confederation': entry.get('ConfederationName', ''),
            'PubDate': pub_date,
        }
        rows.append(row)

    return rows


def save_country_csv(country_code, rows):
    """保存单个国家的CSV文件"""
    if not rows:
        return

    filename = os.path.join(OUTPUT_DIR, f"{country_code}_rankings.csv")
    fieldnames = ['CountryCode', 'CountryName', 'Rank', 'PrevRank',
                  'TotalPoints', 'PrevPoints', 'Matches', 'RankingMovement',
                  'Confederation', 'PubDate']

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"   💾 已保存: {filename} ({len(rows)} 条记录)")


def save_all_countries_csv(all_data):
    """将所有国家的数据合并到一个CSV文件中"""
    if not all_data:
        print("⚠️ 没有数据可保存")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"all_fifa_rankings_{timestamp}.csv")

    fieldnames = ['CountryCode', 'CountryName', 'Rank', 'PrevRank',
                  'TotalPoints', 'PrevPoints', 'Matches', 'RankingMovement',
                  'Confederation', 'PubDate']

    total_rows = 0
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for country_code, rows in all_data.items():
            writer.writerows(rows)
            total_rows += len(rows)

    print(f"\n📊 总CSV文件已保存: {filename}")
    print(f"   共包含 {len(all_data)} 个国家的 {total_rows} 条排名记录")
    return filename


def save_failed_countries(failed_codes):
    """保存失败的国家列表到文件"""
    if not failed_codes:
        return

    filename = os.path.join(OUTPUT_DIR, "failed_countries.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(failed_codes))
    print(f"📝 失败国家列表已保存: {filename}")


def retry_failed_countries(failed_codes):
    """
    重试失败的国家
    返回: (still_failed, retried_success)
    """
    if not failed_codes:
        return [], []

    print(f"\n🔄 开始重试 {len(failed_codes)} 个失败的国家...")
    print("-" * 45)

    still_failed = []
    retried_success = []

    for i, code in enumerate(failed_codes, 1):
        print(f"\n[{i}/{len(failed_codes)}] {code}...")

        rankings, message = fetch_country_ranking_history(code)

        if rankings:
            rows = rankings_to_csv_rows(rankings, code)
            all_data[code] = rows
            save_country_csv(code, rows)
            retried_success.append(code)
            print(f"  ✅ 重试成功!")
        else:
            still_failed.append(code)
            print(f"  ❌ 仍然失败: {message}")

        if i < len(failed_codes):
            time.sleep(REQUEST_DELAY)

    return still_failed, retried_success


def main():
    global all_data  # 用于重试函数

    print("=" * 70)
    print("🏆 FIFA国家队排名历史数据抓取工具 v4")
    print("   (自动重试 + 失败国家单独重试)")
    print("=" * 70)

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--retry":
        # 重试模式
        failed_file = os.path.join(OUTPUT_DIR, "failed_countries.txt")
        if not os.path.exists(failed_file):
            print(f"❌ 找不到失败国家列表: {failed_file}")
            print("   请先运行完整抓取")
            sys.exit(1)

        with open(failed_file, 'r', encoding='utf-8') as f:
            failed_codes = [line.strip() for line in f if line.strip()]

        if not failed_codes:
            print("✅ 没有需要重试的国家")
            sys.exit(0)

        print(f"📋 从文件读取到 {len(failed_codes)} 个失败国家")

        # 加载已有数据
        all_data = {}
        for code in failed_codes:
            csv_file = os.path.join(OUTPUT_DIR, f"{code}_rankings.csv")
            if os.path.exists(csv_file):
                import pandas as pd
                df = pd.read_csv(csv_file)
                rows = df.to_dict('records')
                all_data[code] = rows

        still_failed, retried_success = retry_failed_countries(failed_codes)

        # 更新失败列表
        save_failed_countries(still_failed)

        print(f"\n{'=' * 45}")
        print(f"📊 重试完成统计：")
        print(f"   ✅ 重试成功: {len(retried_success)} 个")
        print(f"   ❌ 仍然失败: {len(still_failed)} 个")
        print(f"{'=' * 45}")

        return

    # 检查输入文件
    if not check_file_exists(INPUT_FILE):
        print(f"\n💡 提示: 请将 '{INPUT_FILE}' 放在以下目录:")
        print(f"   {os.getcwd()}")
        sys.exit(1)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 输出目录: {os.path.abspath(OUTPUT_DIR)}/")

    # 第一步：解析国家短码
    print("\n📋 第一步：从JSON解析国家短码...")
    country_codes = parse_country_codes(INPUT_FILE)

    if not country_codes:
        print("❌ 未找到任何国家短码")
        sys.exit(1)

    # 第二步：逐个请求各国数据（带重试）
    print(f"\n🌐 第二步：开始请求各国排名数据")
    print(f"   共 {len(country_codes)} 个国家")
    print(f"   请求间隔: {REQUEST_DELAY}秒")
    print(f"   最大重试: {MAX_RETRIES}次")
    print("-" * 55)

    all_data = {}
    failed_codes = []
    success_count = 0
    fail_count = 0

    for i, code in enumerate(country_codes, 1):
        progress = f"[{i}/{len(country_codes)}]"
        print(f"\n{progress} {code}...")

        rankings, error_msg, attempts = fetch_with_retry(code)

        if rankings:
            rows = rankings_to_csv_rows(rankings, code)
            all_data[code] = rows
            save_country_csv(code, rows)
            success_count += 1
            print(f"  ✅ 成功! (尝试{attempts}次)")
        else:
            failed_codes.append(code)
            fail_count += 1
            print(f"  ❌ 失败: {error_msg} (尝试{attempts}次)")

        # 请求间隔（除了最后一个）
        if i < len(country_codes):
            print(f"   ⏳ 等待 {REQUEST_DELAY} 秒...")
            time.sleep(REQUEST_DELAY)

    # 第三步：保存总CSV和失败列表
    print("\n" + "-" * 55)
    print(f"📊 抓取完成统计：")
    print(f"   ✅ 成功: {success_count} 个国家")
    print(f"   ❌ 失败: {fail_count} 个国家")

    if failed_codes:
        print(f"\n📋 失败国家列表:")
        for code in failed_codes:
            print(f"   - {code}")

    saved_file = save_all_countries_csv(all_data)
    save_failed_countries(failed_codes)

    if failed_codes:
        print(f"\n💡 提示: 要重试失败的国家，请运行:")
        print(f"   python {sys.argv[0]} --retry")

    print("\n" + "=" * 70)
    print("🎉 全部完成！")
    print("=" * 70)


if __name__ == "__main__":
    # 全局变量
    all_data = {}
    main()
