import os
import json
import time
import pandas as pd
import sys
import re
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

# 載入 .env 中的 API KEY
load_dotenv()

# 定義情感分析分類項目
SENTIMENT_ITEMS = ["正面情感", "負面情感", "中立情感", "情感強度"]

def parse_response(response_text):
    """
    解析 Gemini API 回應，提取 JSON 結果。
    """
    cleaned = response_text.strip()
    
    # 提取 JSON 物件
    json_matches = re.findall(r'\{.*?\}', cleaned, re.DOTALL)
    results = []

    for json_text in json_matches:
        try:
            result = json.loads(json_text)
            for item in SENTIMENT_ITEMS:
                if item not in result:
                    result[item] = ""
            results.append(result)
        except json.JSONDecodeError as e:
            print(f"解析 JSON 失敗：{e}")
            print("錯誤 JSON 內容：", json_text)
            results.append({item: "" for item in SENTIMENT_ITEMS})
    
    return results if results else [{item: "" for item in SENTIMENT_ITEMS}]

def select_dialogue_column(chunk: pd.DataFrame) -> str:
    """
    自動選擇包含對話的欄位，優先檢查常見名稱。
    """
    preferred = ["text", "utterance", "content", "dialogue"]
    for col in preferred:
        if col in chunk.columns:
            return col
    print("CSV 欄位：", list(chunk.columns))
    return chunk.columns[0]
#HW2
def process_batch_dialogue(client, dialogues: list, delimiter="\n###\n"):
    """
    批量處理對話，送入 Gemini API 分析。
    """
    prompt = (
        "你是一位情感分析專家，請對以下顧客服務對話進行情感分析，"
        "回傳 **嚴格符合 JSON 格式** 的結果。\n"
        "請使用 JSON 格式，每筆結果應該長這樣：\n"
        "```json\n"
        "{\n"
        "  \"正面情感\": \"1\" 或 \"\",\n"
        "  \"負面情感\": \"1\" 或 \"\",\n"
        "  \"中立情感\": \"1\" 或 \"\",\n"
        "  \"情感強度\": \"低\" / \"中\" / \"高\"\n"
        "}\n"
        "```\n"
        "請不要加入額外的解釋文字，只回傳 JSON 格式。"
    )
    batch_text = f"{delimiter}".join(dialogues)
    content = prompt + "\n\n" + batch_text

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=content
        )
    except ServerError as e:
        print(f"API 呼叫失敗：{e}")
        return [{item: "" for item in SENTIMENT_ITEMS} for _ in dialogues]
    
    print("API 回傳內容：", response.text)
    parts = response.text.split(delimiter)
    
    results = []
    for part in parts:
        part = part.strip()
        if part:
            results.extend(parse_response(part))  # 解析 JSON

    # 確保結果數量與輸入對話數一致
    if len(results) > len(dialogues):
        results = results[:len(dialogues)]
    elif len(results) < len(dialogues):
        results.extend([{item: "" for item in SENTIMENT_ITEMS}] * (len(dialogues) - len(results)))
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python sentiment_analysis.py <path_to_csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = "sentiment_results.csv"
    if os.path.exists(output_csv):
        os.remove(output_csv)
    
    df = pd.read_csv(input_csv)
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("請設定環境變數 GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_api_key)
    
    dialogue_col = select_dialogue_column(df)
    print(f"使用欄位作為分析對象：{dialogue_col}")
    
    batch_size = 5
    total = len(df)
    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch = df.iloc[start_idx:end_idx]
        dialogues = batch[dialogue_col].tolist()
        dialogues = [str(d).strip() for d in dialogues]
        batch_results = process_batch_dialogue(client, dialogues)
        batch_df = batch.copy()
        for item in SENTIMENT_ITEMS:
            batch_df[item] = [res.get(item, "") for res in batch_results]
        if start_idx == 0:
            batch_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        else:
            batch_df.to_csv(output_csv, mode='a', index=False, header=False, encoding="utf-8-sig")
        print(f"已處理 {end_idx} 筆 / {total}")
        time.sleep(1)
    
    print("全部處理完成。最終結果已寫入：", output_csv)

if __name__ == "__main__":
    main()
