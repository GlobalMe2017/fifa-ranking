# FIFA 国家队排名历史数据抓取工具
从 FIFA 官方 API 抓取 211 个国家队的历史排名数据（1992年至今），支持自动重试和断点续传。

# 功能特性
全覆盖：抓取 FIFA 全部 211 个成员国的历史排名数据
全历史：从 1992 年至今的每一次排名更新
自动重试：网络错误自动重试（10秒→30秒→60秒递进等待）
断点续传：失败国家单独保存，支持命令行重试
高效稳定：每次请求间隔 2 秒，211 个国家约 10 分钟完成
结构化输出：直接生成可用于 MySQL 导入的 CSV 文件

# 环境要求
Python 3.7+，依赖包：requests
pip install requests
快速开始
1. 准备输入文件
将 FIFA API 成功响应的 JSON 数据保存为 fifa_api_success.txt，放在脚本同级目录下。
文件格式要求：
{
  "Results": [
    {
      "IdCountry": "ARG",
      "TeamName": [{"Description": "Argentina"}],
      "Rank": 1
    }
  ]
}

2. 运行抓取
完整抓取所有国家：python fifa_scraper.py
重试之前失败的国家：python fifa_scraper.py --retry

3. 输出文件
抓取完成后，在 fifa_rankings_output/ 目录下生成：
all_fifa_rankings_YYYYMMDD_HHMMSS.csv：全部国家合并数据（约 70000 条）
XXX_rankings.csv：单个国家数据（如 ARG_rankings.csv）
failed_countries.txt：抓取失败的国家列表

# 技术原理
API 接口：GET https://inside.fifa.com/api/rankings/by-country?gender=1&countryCode=ARG&locale=en
请求频率控制：每次请求间隔 2 秒，重试策略为失败后依次等待 10秒 → 30秒 → 60秒，最大重试次数 3 次
数据量预估：211 个国家，每条记录约 200-400 期排名，总计约 70,000 条排名记录，完成时间约 10-15 分钟

# 常见问题
遇到 403 Forbidden 怎么办：检查 HEADERS 中的 User-Agent 是否与当前浏览器一致，必要时更新 Cookie。
抓取过程中断了怎么办：重新运行脚本会自动跳过已成功的国家，只重试失败的国家，使用命令 python fifa_scraper.py --retry
如何获取 fifa_api_success.txt：在浏览器中访问 FIFA 排名页面，打开开发者工具（F12）→ Network 标签，找到 rankingsbyschedule 请求，复制 Response 内容保存即可。


# FIFA National Team Rankings History Scraper
Fetch historical FIFA rankings data for all 211 national teams (from 1992 to present) from the official FIFA API, with auto-retry and resume support.

# Features
Full coverage: All 211 FIFA member nations
Complete history: Every ranking update since 1992
Auto retry: Progressive waiting (10s → 30s → 60s) on network errors
Resume support: Failed countries saved separately, retry via command line
Efficient: 2-second interval between requests, completes in ~10 minutes
Structured output: CSV files ready for MySQL import

# Requirements
Python 3.7+, dependency: requests
pip install requests

# Quick Start
1. Prepare Input File
Save the FIFA API success response JSON as fifa_api_success.txt in the same directory as the script.
Expected format:
{
  "Results": [
    {
      "IdCountry": "ARG",
      "TeamName": [{"Description": "Argentina"}],
      "Rank": 1
    }
  ]
}
2. Run the Scraper
Full scrape all countries: python fifa_scraper.py
Retry previously failed countries: python fifa_scraper.py --retry
3. Output Files
After completion, files are generated in fifa_rankings_output/:
all_fifa_rankings_YYYYMMDD_HHMMSS.csv: Combined data for all countries (~70,000 records)
XXX_rankings.csv: Individual country data (e.g., ARG_rankings.csv)
failed_countries.txt: List of countries that failed to fetch

# Technical Details
API Endpoint: GET https://inside.fifa.com/api/rankings/by-country?gender=1&countryCode=ARG&locale=en
Rate Limiting: 2-second interval between requests. Retry strategy: wait 10s → 30s → 60s on failure, maximum 3 retries.
Data Volume: 211 countries, approximately 200-400 ranking periods per country, totaling ~70,000 records. Estimated completion time: 10-15 minutes.

# FAQ
Encountering 403 Forbidden: 
Check that the User-Agent in HEADERS matches your browser. Update cookies if necessary.

Scraping interrupted: 
Re-run the script, it will automatically skip successfully fetched countries and only retry failed ones using: 
python fifa_scraper.py --retry

How to get fifa_api_success.txt: Open the FIFA rankings page in your browser, press F12 to open Developer Tools, go to Network tab, find the rankingsbyschedule request, copy the Response content and save it.
