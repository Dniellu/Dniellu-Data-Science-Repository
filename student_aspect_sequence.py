# student_aspect_sequence.py

import pandas as pd
import re

# 載入美術生訪談資料
df = pd.read_csv("art_class_interview.csv")

# 美術創作過程相關構面與關鍵詞定義
keyword_map = {
    "靈感來源": ["靈感", "啟發", "看到", "經驗", "感受", "回憶", "夢", "情緒"],
    "主題發想": ["主題", "想法", "構思", "討論", "內容", "概念"],
    "資料蒐集": ["查資料", "參考", "收集", "搜尋", "研究", "看作品", "問老師"],
    "媒材技法": ["技法", "媒材", "筆", "顏料", "色彩", "水彩", "油畫", "拼貼", "素描"],
    "創作實作": ["畫", "做", "創作", "製作", "完成", "處理", "加工", "組合"],
    "修正與調整": ["修改", "重畫", "重做", "調整", "改善", "失敗", "卡住"],
    "自我評價": ["覺得", "滿意", "不錯", "還好", "後悔", "反省", "學到"]
}

def classify_aspects(text):
    found = set()
    for aspect, keywords in keyword_map.items():
        for kw in keywords:
            if re.search(kw, text, flags=re.IGNORECASE):
                found.add(aspect)
    return list(found)

# 分析每位學生的構面順序
student_aspect_sequence = {}
for student, group in df.groupby("who"):
    sequence = []
    prev = None
    for content in group["text"]:
        for aspect in classify_aspects(content):
            if aspect != prev:
                sequence.append(aspect)
                prev = aspect
    student_aspect_sequence[student] = sequence

# 輸出結果
for student, seq in student_aspect_sequence.items():
    print(f"{student} 的構面順序：{' ➜ '.join(seq)}")
