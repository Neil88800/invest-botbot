import yt_dlp
import google.generativeai as genai
import os
import time
import pathlib
import warnings
from types import SimpleNamespace
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi

warnings.filterwarnings("ignore")

GEMINI_API_KEY = "AIzaSyBfyklCufd-mWGmmj9ciCNJeLNS5OQIArI"
genai.configure(api_key=GEMINI_API_KEY)

def format_date(yt_date_str):
    try:
        return datetime.strptime(yt_date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def get_latest_video_robust(channel_url, cookie_file=None):
    """加入 cookie_file 參數"""
    urls_to_try = [f"{channel_url}/streams", f"{channel_url}/videos", channel_url]
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 1,
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # 如果有 cookies，加入設定
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    for url in urls_to_try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    video_data = info['entries'][0]
                    if 'id' in video_data and 'title' in video_data:
                        raw_date = video_data.get('upload_date', datetime.now().strftime("%Y%m%d"))
                        return SimpleNamespace(
                            yt_videoid=video_data['id'],
                            title=video_data['title'],
                            link=f"https://www.youtube.com/watch?v={video_data['id']}",
                            upload_date=format_date(raw_date)
                        )
        except: continue
    return None

def get_transcript(video_id, cookie_file=None):
    """加入 cookie_file 參數"""
    try:
        # 使用 cookies 進行驗證
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_file)
        try:
            t = transcript_list.find_transcript(['zh-TW', 'zh-Hant', 'zh'])
        except:
            t = transcript_list.find_generated_transcript(['zh'])
        return " ".join([item['text'] for item in t.fetch()])
    except:
        return None

def download_audio(url, cookie_file=None):
    """加入 cookie_file 參數"""
    ydl_opts = {
        'format': 'worstaudio/worst',
        'outtmpl': 'temp_%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '64'}],
        'quiet': True, 
        'no_warnings': True,
        'nocheckcertificate': True,
    }
    
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return pathlib.Path(f"temp_{info['id']}.mp3")
    except Exception as e:
        print(f"DL Error: {e}")
        return None

def get_gemini_model():
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in all_models:
            if "gemini-1.5-flash" in m and "latest" not in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel("gemini-1.5-flash")
    except: return genai.GenerativeModel("models/gemini-1.5-flash")

def analyze_video(video_title, content_input, channel_name, input_type="text"):
    model = get_gemini_model()
    
    base_prompt = f"""
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
        if input_type == "audio":
            myfile = genai.upload_file(content_input)
            while myfile.state.name == "PROCESSING":
                time.sleep(2)
                myfile = genai.get_file(myfile.name)
            response = model.generate_content([base_prompt, myfile], safety_settings=safety)
            myfile.delete()
            return response.text
        else:
            full_prompt = base_prompt + f"\n\n【逐字稿】：\n{content_input[:30000]}"
            response = model.generate_content(full_prompt, safety_settings=safety)
            return response.text
    except Exception as e: return f"Error: {e}"

def compare_trends(gooaye_report, miula_report):
    model = get_gemini_model()
    prompt = f"""
    你是投資策略總監。請比對以下兩份報告。
    【A 股癌】{gooaye_report['upload_date']} {gooaye_report['title']}\n{gooaye_report['content'][:3000]}
    【B M觀點】{miula_report['upload_date']} {miula_report['title']}\n{miula_report['content'][:3000]}
    
    【產出「多空對照戰略報告」】：
    1. **共識聚焦**
    2. **多空分歧**
    3. **綜合投資戰略**
    """
    response = model.generate_content(prompt)
    return response.text
