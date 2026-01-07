import streamlit as st
import core
import database
import os

st.set_page_config(page_title="投資情報戰情室", layout="wide", initial_sidebar_state="expanded")
database.init_db()

st.sidebar.title("🚀 投資戰情室")
page = st.sidebar.radio("功能導航", ["📊 戰情儀表板", "⚖️ 多空對照與趨勢", "🗃️ 歷史資料庫"])

CHANNELS = [
    {"name": "股癌 Gooaye", "url": "https://www.youtube.com/@Gooaye"},
    {"name": "M觀點 MiuLa", "url": "https://www.youtube.com/@miulaviewpoint"}
]

def run_analysis_pipeline(channel_config, status, progress):
    try:
        name = channel_config['name']
        status.info(f"📡 [{name}] 掃描最新發布...")
        video = core.get_latest_video_robust(channel_config['url'])
        
        if not video:
            status.error(f"❌ [{name}] 找不到影片 (RSS/網頁讀取失敗)。")
            return None

        # 檢查資料庫
        if database.check_video_exists(video.yt_videoid):
            progress.progress(100)
            status.success(f"✅ [{name}] 最新影片 ({video.upload_date}) 已有紀錄。")
            return {"title": video.title, "skipped": True}

        status.warning(f"🚀 [{name}] 新片 ({video.upload_date})：{video.title}，開始分析...")
        progress.progress(20)
        
        # === 核心修改：混合戰略 ===
        analysis_result = ""
        
        # 策略 A: 嘗試抓取字幕 (雲端最穩)
        status.info(f"📜 [{name}] 嘗試讀取字幕...")
        transcript = core.get_transcript(video.yt_videoid)
        
        if transcript:
            progress.progress(60)
            status.info(f"🤖 [{name}] 字幕讀取成功，AI 分析中...")
            analysis_result = core.analyze_video(video.title, transcript, name, input_type="text")
        else:
            # 策略 B: 字幕失敗，嘗試下載音訊
            status.warning(f"⚠️ [{name}] 無字幕，轉為下載音訊 (可能需較長時間)...")
            audio_path = core.download_audio(video.link)
            
            if audio_path and os.path.exists(audio_path):
                progress.progress(60)
                status.info(f"🤖 [{name}] 音訊下載成功，AI 分析中...")
                analysis_result = core.analyze_video(video.title, audio_path, name, input_type="audio")
                try: os.remove(audio_path)
                except: pass
            else:
                status.error(f"❌ [{name}] 無法取得內容 (無字幕且音訊下載被阻擋)。")
                return None

        progress.progress(90)
        
        # 存檔
        database.save_report(name, video.yt_videoid, video.title, video.upload_date, analysis_result, video.link)
        
        progress.progress(100)
        status.success(f"🎉 [{name}] 分析完成！")
        return {"title": video.title, "content": analysis_result, "skipped": False}
        
    except Exception as e:
        status.error(f"Error: {e}")
        return None

# === 以下介面程式碼維持不變 (直接使用上次提供的 app.py 內容即可) ===
# 為了完整性，若您是全選複製，請保留上次 app.py 後半段 (Page 1, 2, 3 的 UI 邏輯)
# 這裡簡單補上 Page 1 的開頭以確保結構完整：

if page == "📊 戰情儀表板":
    st.title("📊 投資情報戰情室")
    
    if st.button("🔥 一鍵更新所有頻道", type="primary", use_container_width=True):
        for ch in CHANNELS:
            st.divider()
            s = st.empty()
            p = st.progress(0)
            res = run_analysis_pipeline(ch, s, p)
            if res and not res.get("skipped"):
                with st.expander(f"查看報告", expanded=True):
                    st.markdown(res["content"])
        st.success("任務完成")

    # (個別操作區塊...)
    st.markdown("### 📺 個別操作")
    cols = st.columns(2)
    for i, ch in enumerate(CHANNELS):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(ch['name'])
                if st.button(f"檢查更新", key=ch['name']):
                    s = st.empty()
                    p = st.progress(0)
                    res = run_analysis_pipeline(ch, s, p)
                    if res and not res.get("skipped"):
                        st.markdown(res["content"])

# (Page 2, 3 程式碼同上一版，此處省略以節省篇幅，請保留原樣)
elif page == "⚖️ 多空對照與趨勢":
    # ... (貼上之前的代碼)
    st.title("⚖️ 多空對照與趨勢分析")
    if st.button("🚀 執行最新趨勢對照分析", type="primary"):
        with st.spinner("🔍 撈取最新資料..."):
            g = database.get_latest_report("股癌 Gooaye")
            m = database.get_latest_report("M觀點 MiuLa")
            if g and m:
                with st.spinner("🤖 AI 比對中..."):
                    res = core.compare_trends(g, m)
                    database.save_comparison(g['title'], m['title'], res)
                    st.markdown(res)
            else:
                st.error("資料不足")
    
    st.divider()
    df = database.get_all_comparisons()
    if not df.empty:
        for i, r in df.iterrows():
            with st.expander(f"{r['date']} | {r['gooaye_ref']} vs {r['miula_ref']}"):
                st.markdown(r['content'])

elif page == "🗃️ 歷史資料庫":
    # ... (貼上之前的代碼)
    st.title("🗃️ 歷史情報資料庫")
    df = database.get_all_reports()
    if not df.empty:
        st.dataframe(df[['upload_date', 'channel', 'title']], use_container_width=True)
        sel = st.selectbox("選擇報告", df['title'].unique())
        if sel:
            row = df[df['title'] == sel].iloc[0]
            st.info(f"日期: {row['upload_date']}")
            st.markdown(row['content'])
