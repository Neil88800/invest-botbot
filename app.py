import streamlit as st
import core
import database
import os
import time

st.set_page_config(page_title="投資情報戰情室", layout="wide", initial_sidebar_state="expanded")
database.init_db()

st.sidebar.title("🚀 投資戰情室")

# === 【關鍵新增】Cookies 上傳區 ===
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 解鎖 YouTube")
st.sidebar.info("雲端環境易被 YouTube 阻擋，請上傳 cookies.txt 以驗證身分。")
uploaded_cookies = st.sidebar.file_uploader("上傳 cookies.txt", type="txt", key="cookie_uploader")

cookie_path = None
if uploaded_cookies is not None:
    # 將上傳的檔案存到暫存檔
    with open("temp_cookies.txt", "wb") as f:
        f.write(uploaded_cookies.getbuffer())
    cookie_path = "temp_cookies.txt"
    st.sidebar.success("✅ Cookies 已載入")
else:
    st.sidebar.warning("⚠️ 未載入 Cookies (可能導致下載失敗)")

page = st.sidebar.radio("功能導航", ["📊 戰情儀表板", "⚖️ 多空對照與趨勢", "🗃️ 歷史資料庫"])

CHANNELS = [
    {"name": "股癌 Gooaye", "url": "https://www.youtube.com/@Gooaye"},
    {"name": "M觀點 MiuLa", "url": "https://www.youtube.com/@miulaviewpoint"}
]

def run_analysis_pipeline(channel_config, status, progress, cookie_file=None):
    try:
        name = channel_config['name']
        status.info(f"📡 [{name}] 掃描最新發布...")
        
        # 傳入 cookie_file
        video = core.get_latest_video_robust(channel_config['url'], cookie_file)
        
        if not video:
            status.error(f"❌ [{name}] 找不到影片 (請檢查網路或 Cookies)。")
            return None

        if database.check_video_exists(video.yt_videoid):
            progress.progress(100)
            status.success(f"✅ [{name}] 最新影片 ({video.upload_date}) 已有紀錄。")
            return {"title": video.title, "skipped": True}

        status.warning(f"🚀 [{name}] 新片 ({video.upload_date})：{video.title}，開始分析...")
        progress.progress(20)
        
        analysis_result = ""
        
        # 策略 A: 嘗試抓取字幕 (傳入 cookies)
        status.info(f"📜 [{name}] 嘗試讀取字幕...")
        transcript = core.get_transcript(video.yt_videoid, cookie_file)
        
        if transcript:
            progress.progress(60)
            status.info(f"🤖 [{name}] 字幕讀取成功，AI 分析中...")
            analysis_result = core.analyze_video(video.title, transcript, name, input_type="text")
        else:
            # 策略 B: 下載音訊 (傳入 cookies)
            status.warning(f"⚠️ [{name}] 無字幕，轉為下載音訊 (需較久)...")
            audio_path = core.download_audio(video.link, cookie_file)
            
            if audio_path and os.path.exists(audio_path):
                progress.progress(60)
                status.info(f"🤖 [{name}] 音訊下載成功，AI 分析中...")
                analysis_result = core.analyze_video(video.title, audio_path, name, input_type="audio")
                try: os.remove(audio_path)
                except: pass
            else:
                status.error(f"❌ [{name}] 無法取得內容 (請確認 Cookies 是否有效)。")
                return None

        progress.progress(90)
        database.save_report(name, video.yt_videoid, video.title, video.upload_date, analysis_result, video.link)
        progress.progress(100)
        status.success(f"🎉 [{name}] 分析完成！")
        return {"title": video.title, "content": analysis_result, "skipped": False}
        
    except Exception as e:
        status.error(f"Error: {e}")
        return None

# === 分頁 1: 戰情儀表板 ===
if page == "📊 戰情儀表板":
    st.title("📊 投資情報戰情室")
    
    if st.button("🔥 一鍵更新所有頻道", type="primary", use_container_width=True):
        if not cookie_path:
            st.error("⚠️ 強烈建議先在側邊欄上傳 cookies.txt，否則極可能失敗！")
        
        for ch in CHANNELS:
            st.divider()
            s = st.empty()
            p = st.progress(0)
            # 傳遞 cookie_path
            res = run_analysis_pipeline(ch, s, p, cookie_path)
            if res and not res.get("skipped"):
                with st.expander(f"查看報告", expanded=True):
                    st.markdown(res["content"])
        st.success("任務完成")

    st.markdown("### 📺 個別操作")
    cols = st.columns(2)
    for i, ch in enumerate(CHANNELS):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(ch['name'])
                if st.button(f"檢查更新", key=ch['name']):
                    s = st.empty()
                    p = st.progress(0)
                    res = run_analysis_pipeline(ch, s, p, cookie_path)
                    if res and not res.get("skipped"):
                        st.markdown(res["content"])

# === 分頁 2: 多空對照與趨勢 ===
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

# === 分頁 3: 歷史資料庫 ===
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
