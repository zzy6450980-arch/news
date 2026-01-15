import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from openai import OpenAI
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="备考新闻AI助手", layout="wide")

st.title("📚 行测 & 校招：时政热点 AI 助手")
st.markdown("该工具自动抓取人民网最新动态，并调用 AI 提取考试重点。")

# --- 侧边栏：配置 ---
st.sidebar.header("⚙️ 配置中心")
api_key = 'sk-4c969651e5bf4a6491b9218b748f8647'
selected_channels = st.sidebar.multiselect(
    "选择采集板块",
    ["经济科技", "社会法治", "文旅体育", "国际新闻",'党政新闻','党政新闻','军事新闻','大湾区新闻','台湾新闻','教育新闻'],
    default=["经济科技", "社会法治", "文旅体育", "国际新闻",'党政新闻','党政新闻','军事新闻','大湾区新闻','台湾新闻','教育新闻']
)

# 频道 URL 映射
CHANNEL_MAP = {
    "经济科技": "http://finance.people.com.cn",
    "社会法治": "http://society.people.com.cn",
    "文旅体育": "http://ent.people.com.cn",
    "国际新闻": "http://world.people.com.cn",
    '党政新闻': 'http://cpc.people.com.cn',
    '军事新闻': 'http://military.people.com.cn',
    '大湾区新闻':'http://gba.people.cn',
    '台湾新闻':'http://tw.people.com.cn',
    '教育新闻':'http://edu.people.com.cn',
}


# --- 核心逻辑：采集 ---
def fetch_news(channels):
    all_news = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for name in channels:
        url = CHANNEL_MAP[name]
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 抓取 2026 年链接
            links = soup.find_all('a', href=re.compile(r'/n1/2026/'))
            seen = set()
            for a in links[:50]:
                t = a.get_text(strip=True)
                if len(t) > 12 and t not in seen:
                    all_news.append({"板块": name, "新闻标题": t,
                                     "链接": url + a.get('href') if not a.get('href').startswith('http') else a.get(
                                         'href')})
                    seen.add(t)
        except Exception as e:
            st.error(f"抓取 {name} 失败: {e}")
    return pd.DataFrame(all_news)


# --- 核心逻辑：AI 分析 ---
def get_ai_analysis(news_df, key):
    client = OpenAI(api_key= api_key, base_url="https://api.deepseek.com")
    titles = "\n".join([f"[{row['板块']}] {row['新闻标题']}" for _, row in news_df.iterrows()])

    prompt = (f"你是一名公职考试培训专家。请从以下人民网新闻标题中选出5-8个最重要的考点。要求："
              f"首先通过标题以及爬取到的网址搜索并阅读完整报道内容，列出这条新闻在人民网发出的时间；其次根据报道内容总结提炼出内容核心，"
              f"按照时间、地点、人物、起因、经过、结果这六要素进行总结，最后指明新闻是哪个方面的、可能与什么考点有关。针对行测常识、申论及银行/国企校招；\n\n新闻列表：\n{titles}")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# --- 页面交互逻辑 ---
if st.button("🚀 开始采集并生成简报"):
    if not selected_channels:
        st.warning("请至少选择一个板块")
    else:
        with st.spinner("正在爬取实时数据..."):
            df = fetch_news(selected_channels)

        if not df.empty:
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("📰 实时新闻列表")
                st.dataframe(df, use_container_width=True)
                # 提供 CSV 下载
                csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 下载新闻 CSV", data=csv, file_name="news.csv", mime="text/csv")

            with col2:
                st.subheader("📝 AI 备考精简")
                if api_key:
                    with st.spinner("AI 正在深度思考考点..."):
                        analysis = get_ai_analysis(df, api_key)
                        st.markdown(analysis)
                else:
                    st.info("💡 请在侧边栏输入 API Key 以开启 AI 考点分析功能。")
        else:
            st.error("未能采集到数据，请检查网络。")
