# EMOwithSnow.py

import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import json
from snownlp import SnowNLP
import re
from collections import defaultdict, Counter

matplotlib.use('Agg')
matplotlib.rc('font', family='Microsoft JhengHei')

# 🔐 確保 static 永遠指向 ./static（專案資料夾下）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "static")
os.makedirs(output_dir, exist_ok=True)

# 美術學習構面分類關鍵字
keyword_map = {
    "課程內容": ["上課", "教學", "課程", "練習", "技巧", "作業", "練圖"],
    "創作經驗": ["創作", "靈感", "構圖", "發想", "畫畫", "表現", "表達"],
    "老師互動": ["老師", "指導", "建議", "鼓勵", "批評", "教", "回饋"],
    "同儕互動": ["同學", "討論", "合作", "一起", "朋友", "互相"],
    "學習困難": ["困難", "壓力", "不會", "卡住", "煩惱", "挫折"],
    "成就與成長": ["進步", "開心", "滿意", "學到", "收穫", "成就"]
}

def classify_aspects(text):
    found = set()
    for aspect, keywords in keyword_map.items():
        for kw in keywords:
            if re.search(kw, text, flags=re.IGNORECASE):
                found.add(aspect)
    return list(found)

def generate_analysis(user_id, df):
    moodtrend_path = os.path.join(output_dir, f"moodtrend_{user_id}.png")
    aspect_bar_path = os.path.join(output_dir, f"aspect_bar_{user_id}.png")
    sequence_json_path = os.path.join(output_dir, f"aspect_sequence_{user_id}.json")

    # ✅ 清洗資料：空值處理
    df["text"] = df["text"].fillna("").astype(str)

    # ✅ 移除無效文字
    df = df[df["text"].str.len() > 2].reset_index(drop=True)

    # ✅ 檢查欄位與內容
    if df.empty or "text" not in df.columns or "who" not in df.columns:
        raise ValueError("資料內容為空，或缺少 'text' 或 'who' 欄位，請確認格式。")

    # 分析
    df["sentiment"] = df["text"].apply(lambda x: SnowNLP(x).sentiments)
    df["aspects"] = df["text"].apply(classify_aspects)

    # 🟦 畫情緒趨勢圖
    try:
        if not df["sentiment"].empty and df["sentiment"].nunique() > 1:
            plt.figure(figsize=(10, 4))
            plt.plot(df.index, df["sentiment"], marker="o")
            plt.title("訪談情緒變化趨勢")
            plt.xlabel("發言次序")
            plt.ylabel("情緒值 (0=負面, 1=正面)")
            plt.tight_layout()
            plt.savefig(moodtrend_path)
            plt.close()
    except Exception as e:
        print(f"[⚠️ 畫情緒圖失敗] {e}")

    # 🟨 畫構面比例圖
    all_aspects = [aspect for aspects in df["aspects"] for aspect in aspects]
    aspect_counts = Counter(all_aspects)

    try:
        if aspect_counts:
            plt.figure(figsize=(8, 5))
            plt.bar(aspect_counts.keys(), aspect_counts.values())
            plt.title("藝術學習構面出現比例")
            plt.ylabel("出現次數")
            plt.xticks(rotation=30)
            plt.tight_layout()
            plt.savefig(aspect_bar_path)
            plt.close()
    except Exception as e:
        print(f"[⚠️ 畫構面圖失敗] {e}")

    # 🟩 輸出構面順序 JSON
    student_sequences = {}
    for student, group in df.groupby("who"):
        sequence = []
        prev = None
        for text in group["text"]:
            for aspect in classify_aspects(text):
                if aspect != prev:
                    sequence.append(aspect)
                    prev = aspect
        student_sequences[student] = sequence

    with open(sequence_json_path, "w", encoding="utf-8") as f:
        json.dump(student_sequences, f, ensure_ascii=False, indent=2)

    # ✅ 最後印出確認
    print("🔍 實際儲存檔案：")
    print("情緒圖：", moodtrend_path, "✅" if os.path.exists(moodtrend_path) else "❌")
    print("構面圖：", aspect_bar_path, "✅" if os.path.exists(aspect_bar_path) else "❌")
    print("構面順序 JSON：", sequence_json_path, "✅" if os.path.exists(sequence_json_path) else "❌")

    return {
        "moodtrend_img": os.path.relpath(moodtrend_path, BASE_DIR),
        "aspect_bar_img": os.path.relpath(aspect_bar_path, BASE_DIR),
        "aspect_sequence_json": os.path.relpath(sequence_json_path, BASE_DIR)
    }
