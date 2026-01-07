import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "investment_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 報告表 (新增 upload_date)
    # 注意：SQLite 修改現有欄位比較麻煩，若您那是新專案，建議直接刪除 .db 檔讓它重建
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            video_id TEXT UNIQUE,
            title TEXT,
            upload_date TEXT,  -- 影片上傳日期
            analyze_date TEXT, -- 分析執行日期
            content TEXT,
            url TEXT
        )
    ''')
    
    # 2. 趨勢對照表 (新功能)
    c.execute('''
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,         -- 產出報告日期
            gooaye_ref TEXT,   -- 股癌參考影片標題
            miula_ref TEXT,    -- M觀點參考影片標題
            content TEXT       -- AI 對照分析內容
        )
    ''')
    conn.commit()
    conn.close()

def check_video_exists(video_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM reports WHERE video_id = ?", (video_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_report(channel, video_id, title, upload_date, content, url):
    """儲存單集分析報告"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO reports (channel, video_id, title, upload_date, analyze_date, content, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (channel, video_id, title, upload_date, datetime.now().strftime("%Y-%m-%d %H:%M"), content, url))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def save_comparison(gooaye_title, miula_title, content):
    """【新功能】儲存多空對照報告"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO comparisons (date, gooaye_ref, miula_ref, content)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M"), gooaye_title, miula_title, content))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Save Comparison Error: {e}")
        return False
    finally:
        conn.close()

def get_all_reports():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY upload_date DESC", conn) # 改以 upload_date 排序
    conn.close()
    return df

def get_latest_report(channel_name):
    """取得該頻道「最新」的一筆報告 (依上傳日期)"""
    conn = sqlite3.connect(DB_FILE)
    # 這裡我們取 analyze_date 或 upload_date 皆可，取最新的一筆
    df = pd.read_sql_query(f"SELECT * FROM reports WHERE channel = '{channel_name}' ORDER BY upload_date DESC LIMIT 1", conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

def get_all_comparisons():
    """取得所有對照報告"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM comparisons ORDER BY date DESC", conn)
    conn.close()
    return df