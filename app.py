import streamlit as st
import core
import database
import os

st.set_page_config(page_title="投資情報戰情室", layout="wide", initial_sidebar_state="expanded")
database.init_db()

st.sidebar.title("🚀 投資戰情室")

# Cookies 區塊 (雖然幫助有限，但留著備用)
st.sidebar.markdown("---")
st.sidebar.caption("🔧 設定區")
uploaded_cookies = st.sidebar.file_uploader("上傳 cookies.txt (選用)", type="txt")
cookie_path = None
if uploaded_cookies is not None:
    with open("temp_cookies.txt", "wb") as f: f.write(uploaded_cookies.getbuffer())
    cookie_path = "temp_cookies.txt"
    st.sidebar.success("Cookies 已載入")

page = st.sidebar.radio("功能導航", ["📊 戰情儀表板", "⚖️ 多空對照與趨勢", "🗃️ 歷史資料庫"])

CHANNELS = [
    {"name": "股癌 Gooaye", "url": "https://www.youtube.com/@Gooaye"},
    {"name": "M觀點 MiuLa", "url": "https://www.youtube.com/@miulaviewpoint"}
]

def process_video_analysis(name, video_obj, status, progress):
    """共用的分析處理邏輯"""
    try:
        # 檢查資料庫
        if database.check_video_exists(video_obj.yt_videoid):
            progress.progress(100)
            status.success(f"✅ [{name}] {video_obj.title} 已有紀錄。")
            return {"title": video_obj.title, "skipped": True}

        status.warning(f"🚀 [{name}] 開始分析：{video_obj.title} ...")
        progress.progress(20)
        
        analysis_result = ""
        
        # 策略 1: 抓字幕 (最優先)
        status.info(f"📜 嘗試讀取字幕...")
        transcript = core.get_transcript(video_obj.yt_videoid, cookie_path)
        
        if transcript:
            progress.progress(60)
            status.info(f"🤖 字幕讀取成功，AI 分析中...")
            analysis_result = core.analyze_video(video_obj.title, transcript, name, input_type="text")
        else:
            # 策略 2: 下載音訊
            status.warning(f"⚠️ 無字幕，嘗試下載音訊 (雲端環境可能失敗)...")
            audio_path = core.download_audio(video_obj.link, cookie_path)
            if audio_path and os.path.exists(audio_path):
                progress.progress(60)
                status.info(f"🤖 音訊下載成功，AI 分析中...")
                analysis_result = core.analyze_video(video_obj.title, audio_path, name, input_type="audio")
                try: os.remove(audio_path)
                except: pass
            else:
                status.error(f"❌ 雲端阻擋：無法下載音訊且無字幕。建議改用本地端執行。")
                return None

        progress.progress(90)
        database.save_report(name, video_obj.yt_videoid, video_obj.title, video_obj.upload_date, analysis_result, video_obj.link)
        progress.progress(100)
        status.success(f"🎉 分析完成！")
        return {"title": video_obj.title, "content": analysis_result, "skipped": False}
    except Exception as e:
        status.error(f"Error: {e}")
        return None

# === 頁面 1 ===
if page == "📊 戰情儀表板":
    st.title("📊 投資情報戰情室")
    
    # 1. 自動掃描區
    st.subheader("📡 自動掃描")
    if st.button("🔥 一鍵更新所有頻道", type="primary"):
        for ch in CHANNELS:
            st.divider()
            s = st.empty()
            p = st.progress(0)
            
            s.info(f"正在掃描 {ch['name']}...")
            video = core.get_latest_video_robust(ch['url'], cookie_path)
            
            if video:
                res = process_video_analysis(ch['name'], video, s, p)
                if res and not res.get("skipped"):
                    with st.expander("查看報告", expanded=True):
                        st.markdown(res["content"])
            else:
                s.error(f"❌ {ch['name']} 掃描失敗 (RSS/網頁被擋)")

    st.divider()
    
    # 2. 手動救援區 (新功能)
    st.subheader("🔧 手動分析 (救援模式)")
    st.caption("如果自動掃描一直失敗，請直接貼上影片網址")
    
    col_input, col_act = st.columns([3, 1])
    with col_input:
        manual_url = st.text_input("貼上 YouTube 影片網址", placeholder="https://www.youtube.com/watch?v=...")
        manual_channel = st.selectbox("選擇頻道歸屬", ["股癌 Gooaye", "M觀點 MiuLa"])
    
    with col_act:
        st.write("")
        st.write("")
        if st.button("手動執行分析"):
            if "v=" in manual_url:
                vid = manual_url.split("v=")[1].split("&")[0]
                # 建立一個假 Video 物件
                from types import SimpleNamespace
                from datetime import datetime
                manual_video = SimpleNamespace(
                    yt_videoid=vid,
                    title="手動指定影片", # 先暫定，AI 分析時不影響
                    link=manual_url,
                    upload_date=datetime.now().strftime("%Y-%m-%d")
                )
                
                s = st.empty()
                p = st.progress(0)
                res = process_video_analysis(manual_channel, manual_video, s, p)
                if res:
                    st.markdown(res["content"])
            else:
                st.error("網址格式錯誤")

# === 頁面 2 & 3 維持不變 (請保留之前的代碼) ===
elif page == "⚖️ 多空對照與趨勢":
    st.title("⚖️ 多空對照與趨勢分析")
    if st.button("🚀 執行最新趨勢對照分析", type="primary"):
        with st.spinner("🔍 撈取最新資料..."):
            g = database.get_latest_report("股癌 Gooaye")
            m = database.get_latest_report("M觀點 MiuLa")
            if g is not None and m is not None:
                st.info(f"📌 比對標的：\n- 股癌：{g['upload_date']} {g['title']}\n- M觀點：{m['upload_date']} {m['title']}")
                with st.spinner("🤖 AI 比對中..."):
                    res = core.compare_trends(g, m)
                    database.save_comparison(g['title'], m['title'], res)
                    st.markdown(res)
            else:
                st.error("資料不足，請先更新分析報告。")
    st.divider()
    df = database.get_all_comparisons()
    if not df.empty:
        for i, r in df.iterrows():
            with st.expander(f"{r['date']} | {r['gooaye_ref']} vs {r['miula_ref']}"):
                st.markdown(r['content'])
    else:
        st.info("尚無紀錄")

elif page == "🗃️ 歷史資料庫":
    st.title("🗃️ 歷史情報資料庫")
    df = database.get_all_reports()
    if not df.empty:
        st.dataframe(df[['upload_date', 'channel', 'title']], use_container_width=True)
        sel = st.selectbox("選擇報告", df['title'].unique())
        if sel:
            row = df[df['title'] == sel].iloc[0]
            st.info(f"日期: {row['upload_date']}")
            st.markdown(row['content'])
    else:
        st.warning("資料庫為空。")
