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
            status.error(f"❌ [{name}] 找不到影片。")
            return None

        # 檢查資料庫
        if database.check_video_exists(video.yt_videoid):
            progress.progress(100)
            status.success(f"✅ [{name}] 最新影片 ({video.upload_date}) 已有紀錄。")
            return {"title": video.title, "skipped": True}

        # 開始處理
        status.warning(f"🚀 [{name}] 發現新片 ({video.upload_date})：{video.title}，開始分析...")
        progress.progress(30)
        
        status.info(f"⬇️ [{name}] 下載音訊...")
        audio_path = core.download_audio(video.link)
        if not audio_path: return None
        progress.progress(60)

        status.info(f"🤖 [{name}] AI 分析中...")
        analysis = core.analyze_video(video.title, audio_path, name)
        progress.progress(90)
        
        # 存檔 (包含 upload_date)
        database.save_report(name, video.yt_videoid, video.title, video.upload_date, analysis, video.link)
        
        try: os.remove(audio_path)
        except: pass
        
        progress.progress(100)
        status.success(f"🎉 [{name}] 分析完成！")
        return {"title": video.title, "content": analysis, "skipped": False}
    except Exception as e:
        status.error(f"Error: {e}")
        return None

# === 分頁 1: 戰情儀表板 ===
if page == "📊 戰情儀表板":
    st.title("📊 投資情報戰情室")
    
    st.markdown("### 🔥 全局指令")
    if st.button("一鍵更新所有頻道 (自動略過舊片)", type="primary", use_container_width=True):
        for ch in CHANNELS:
            st.divider()
            status = st.empty()
            prog = st.progress(0)
            res = run_analysis_pipeline(ch, status, prog)
            if res and not res.get("skipped"):
                with st.expander(f"查看 {ch['name']} 最新報告", expanded=True):
                    st.markdown(res["content"])
        st.success("✅ 所有更新任務完成！")

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

# === 分頁 2: 多空對照與趨勢 ===
elif page == "⚖️ 多空對照與趨勢":
    st.title("⚖️ 多空對照與趨勢分析")
    st.markdown("系統將自動撈取資料庫中 **兩大頻道最新** 的一集報告進行交叉比對，並將結果存入歷史紀錄。")
    
    if st.button("🚀 執行最新趨勢對照分析", type="primary"):
        with st.spinner("🔍 正在撈取資料庫最新報告..."):
            # 1. 撈取兩邊最新的報告
            gooaye_latest = database.get_latest_report("股癌 Gooaye")
            miula_latest = database.get_latest_report("M觀點 MiuLa")
            
            if gooaye_latest is None or miula_latest is None:
                st.error("❌ 資料不足！請先回到「戰情儀表板」執行更新，確保兩大頻道都有至少一筆資料。")
            else:
                st.info(f"📌 鎖定分析標的：\n- 股癌：{gooaye_latest['upload_date']} {gooaye_latest['title']}\n- M觀點：{miula_latest['upload_date']} {miula_latest['title']}")
                
                # 2. AI 比對
                with st.spinner("🤖 AI 正在進行深度交叉比對..."):
                    comparison_result = core.compare_trends(gooaye_latest, miula_latest)
                
                # 3. 存入資料庫
                database.save_comparison(gooaye_latest['title'], miula_latest['title'], comparison_result)
                
                st.success("✅ 分析完成並已存檔！")
                st.markdown("### ⚔️ 最新對照報告")
                st.markdown(comparison_result)

    st.divider()
    st.subheader("📜 歷史對照紀錄")
    comp_df = database.get_all_comparisons()
    
    if not comp_df.empty:
        for index, row in comp_df.iterrows():
            with st.expander(f"📅 {row['date']} | 🆚 {row['gooaye_ref']} vs {row['miula_ref']}"):
                st.markdown(row['content'])
    else:
        st.info("尚無歷史對照紀錄。")

# === 分頁 3: 歷史資料庫 ===
elif page == "🗃️ 歷史資料庫":
    st.title("🗃️ 歷史情報資料庫")
    df = database.get_all_reports()
    
    if not df.empty:
        channel_filter = st.selectbox("頻道篩選", ["全部"] + list(df['channel'].unique()))
        if channel_filter != "全部":
            df = df[df['channel'] == channel_filter]
            
        # 顯示表格 (包含上傳日期)
        st.dataframe(
            df[['upload_date', 'channel', 'title', 'url']], 
            column_config={
                "upload_date": "影片上傳日",
                "channel": "頻道",
                "title": "影片標題",
                "url": st.column_config.LinkColumn("連結")
            },
            use_container_width=True
        )
        
        st.divider()
        st.subheader("📄 報告閱讀")
        selected_report = st.selectbox("選擇報告", df['title'].tolist())
        if selected_report:
            record = df[df['title'] == selected_report].iloc[0]
            st.info(f"📅 上傳日期: {record['upload_date']} | 📺 {record['channel']}")
            st.markdown(record['content'])
    else:
        st.warning("資料庫為空。")