import yt_dlp
import google.generativeai as genai
import os
import time
import pathlib
import warnings
from types import SimpleNamespace
from datetime import datetime

warnings.filterwarnings("ignore")

GEMINI_API_KEY = "AIzaSyBfyklCufd-mWGmmj9ciCNJeLNS5OQIArI"
genai.configure(api_key=GEMINI_API_KEY)

def format_date(yt_date_str):
    """將 YYYYMMDD 轉為 YYYY-MM-DD"""
    try:
        return datetime.strptime(yt_date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def get_latest_video_robust(channel_url):
    urls_to_try = [f"{channel_url}/streams", f"{channel_url}/videos", channel_url]
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 1,
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for url in urls_to_try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    video_data = info['entries'][0]
                    if 'id' in video_data and 'title' in video_data:
                        # 【更新】抓取 upload_date
                        raw_date = video_data.get('upload_date', datetime.now().strftime("%Y%m%d"))
                        formatted_date = format_date(raw_date)
                        
                        return SimpleNamespace(
                            yt_videoid=video_data['id'],
                            title=video_data['title'],
                            link=f"https://www.youtube.com/watch?v={video_data['id']}",
                            upload_date=formatted_date
                        )
        except: continue
    return None

def download_audio(url):
    ydl_opts = {
        'format': 'worstaudio/worst',
        'outtmpl': 'temp_%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '64'}],
        'quiet': True, 'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return pathlib.Path(f"temp_{info['id']}.mp3")
    except: return None

def get_gemini_model():
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in all_models:
            if "gemini-1.5-flash" in m and "latest" not in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel("gemini-1.5-flash")
    except: return genai.GenerativeModel("models/gemini-1.5-flash")

def analyze_video(video_title, audio_path, channel_name):
    model = get_gemini_model()
    prompt = f"""
    你是專業投資分析師。請分析「{channel_name}」的影片「{video_title}」。
    【任務】：忽略閒聊，專注市場趨勢、經濟數據、個股分析。
    【輸出 (繁體中文 Markdown)】：
    1. **核心觀點摘要**
    2. **市場趨勢判讀** (多/空/震盪及其理由)
    3. **重點標的與產業** (表格呈現：標的 | 看法 | 理由)
    4. **投資策略建議**
    5. **風險提示**
    """
    safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
    try:
        myfile = genai.upload_file(audio_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
        response = model.generate_content([prompt, myfile], safety_settings=safety)
        myfile.delete()
        return response.text
    except Exception as e: return f"Error: {e}"

def compare_trends(gooaye_report, miula_report):
    """
    【更新】加入標題與日期的對照分析
    """
    model = get_gemini_model()
    prompt = f"""
    你是投資策略總監。請根據以下兩份最新的分析報告進行深度比對。

    【報告 A：股癌 Gooaye】
    - 日期：{gooaye_report['upload_date']}
    - 標題：{gooaye_report['title']}
    - 內容摘要：
    {gooaye_report['content'][:3000]}

    【報告 B：M觀點 MiuLa】
    - 日期：{miula_report['upload_date']}
    - 標題：{miula_report['title']}
    - 內容摘要：
    {miula_report['content'][:3000]}

    【請產出「多空對照戰略報告」】：
    1. **標的資訊確認**：請先列出這份報告是依據哪兩部影片進行比對的（包含日期）。
    2. **共識聚焦**：兩位分析師一致看好的趨勢或產業 (高確信度訊號)。
    3. **多空分歧**：兩人在哪些觀點上有衝突？(例如一人看多一人保守)。
    4. **綜合投資戰略**：結合兩者觀點，本週最佳的操作建議。
    """
    response = model.generate_content(prompt)
    return response.text