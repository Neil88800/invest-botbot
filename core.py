import yt_dlp
import google.generativeai as genai
import os
import time
import pathlib
import warnings
from types import SimpleNamespace
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import scrapetube  # 【新武器】

warnings.filterwarnings("ignore")

GEMINI_API_KEY = "AIzaSyBfyklCufd-mWGmmj9ciCNJeLNS5OQIArI"
genai.configure(api_key=GEMINI_API_KEY)

def format_date(timestamp):
    try:
        # scrapetube 回傳的是文字發布時間，我們簡化處理，直接回傳當下日期作為標記
        # 或者是解析 timestamp，這裡為了穩定直接用當天日期 (反正目的是為了存檔)
        return datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def get_latest_video_robust(channel_url, cookie_file=None):
    """
    【核心升級】改用 scrapetube 抓取最新影片 ID
    這在雲端環境比 yt-dlp 穩定非常多，不需要 Cookies 也能看到列表
    """
    try:
        # 從 URL 提取 Channel ID (scrapetube 需要 ID)
        # 股癌: UC23rnlQU_qE3cec9x709peA
        # M觀點: UCCvJG2hWbC1V0M5tJ8v3e_A
        channel_id = None
        if "Gooaye" in channel_url: channel_id = "UC23rnlQU_qE3cec9x709peA"
        if "miulaviewpoint" in channel_url: channel_id = "UCCvJG2hWbC1V0M5tJ8v3e_A"
        
        if not channel_id:
            return None

        # 抓取影片 (videos)
        videos = scrapetube.get_channel(channel_id, content_type='videos', limit=1)
        video_list = list(videos)
        
        # 抓取直播 (streams)
        streams = scrapetube.get_channel(channel_id, content_type='streams', limit=1)
        stream_list = list(streams)
        
        # 比較誰比較新 (或是優先選直播)
        target_video = None
        
        # 簡單策略：如果有直播且是最近的，優先選直播
        if stream_list:
            target_video = stream_list[0]
        elif video_list:
            target_video = video_list[0]
            
        if target_video:
            video_id = target_video['videoId']
            title = target_video['title']['runs'][0]['text']
            # scrapetube 不會直接給 upload_date，我們用當下時間代替
            return SimpleNamespace(
                yt_videoid=video_id,
                title=title,
                link=f"https://www.youtube.com/watch?v={video_id}",
                upload_date=datetime.now().strftime("%Y-%m-%d") 
            )
            
    except Exception as e:
        print(f"Scrapetube Error: {e}")
        return None
    return None

def get_transcript(video_id, cookie_file=None):
    try:
        # 雲端 IP 很容易被擋，這裡多加一些 fallback
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_file)
        try:
            t = transcript_list.find_transcript(['zh-TW', 'zh-Hant', 'zh'])
        except:
            t = transcript_list.find_generated_transcript(['zh'])
        return " ".join([item['text'] for item in t.fetch()])
    except:
        return None

def download_audio(url, cookie_file=None):
    # 雲端環境下載音訊失敗率極高，這邊保留但僅作為最後手段
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
    except:
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
    【報告A 股癌】{gooaye_report['upload_date']} {gooaye_report['title']}\n{gooaye_report['content'][:3000]}
    【報告B M觀點】{miula_report['upload_date']} {miula_report['title']}\n{miula_report['content'][:3000]}
    
    【產出「多空對照戰略報告」】：
    1. **共識聚焦**
    2. **多空分歧**
    3. **綜合投資戰略**
    """
    response = model.generate_content(prompt)
    return response.text
