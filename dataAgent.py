import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import requests

def get_world_bank_data(country_code):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/GC.TAX.TOTL.GD.ZS?format=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None

# AI Agent 相關模組
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer

load_dotenv()
#HW1 Prompt change info
async def process_chunk(chunk, start_idx, total_records, model_client, termination_condition):
    """
    處理單一批次的死亡人口數據，
    - 讓 AI 分析年齡、性別對死亡率的影響
    - 使用 MultimodalWebSurfer 搜尋國際統計數據
    - 統整 AI 代理人的回應並返回
    """
    chunk_data = chunk.to_dict(orient='records')
    prompt = (
        f"處理第 {start_idx} 至 {start_idx + len(chunk) - 1} 筆資料（共 {total_records} 筆）。\n"
        f"以下為該批次資料:\n{chunk_data}\n\n"
        "請根據以下重點進行分析：\n"
        "1. 分析不同年齡層與性別的死亡趨勢，找出高風險群體。\n"
        "2. 計算死亡率變化，找出影響死亡率的可能因素（如年齡、疾病等）。\n"
        "3. 請 MultimodalWebSurfer 搜尋國際統計資料，提供參考對比。\n"
        "4. 最後提供完整分析報告與結論。"
    )
    
    data_analyzer = AssistantAgent("DataAnalyzerAgent", model_client)
    statistician = AssistantAgent("StatisticianAgent", model_client)
    web_researcher = MultimodalWebSurfer("WebResearchAgent", model_client)
    user_proxy = UserProxyAgent("UserProxyAgent")
    
    team = RoundRobinGroupChat(
        [data_analyzer, statistician, web_researcher, user_proxy],
        termination_condition=termination_condition
    )
    
    messages = []
    async for event in team.run_stream(task=prompt):
        if isinstance(event, TextMessage):
            print(f"[{event.source}] => {event.content}\n")
            messages.append({
                "batch_start": start_idx,
                "batch_end": start_idx + len(chunk) - 1,
                "source": event.source,
                "content": event.content
            })
    return messages

async def main():
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("請檢查 .env 檔案中的 GEMINI_API_KEY。")
        return
    
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=gemini_api_key,
    )
    #HW1 Data set info
    termination_condition = TextMentionTermination("exit")
    csv_file_path = "opendata107d010.csv"
    chunk_size = 1000
    chunks = list(pd.read_csv(csv_file_path, chunksize=chunk_size))
    total_records = sum(chunk.shape[0] for chunk in chunks)
    
    tasks = [
        process_chunk(chunk, idx * chunk_size, total_records, model_client, termination_condition)
        for idx, chunk in enumerate(chunks)
    ]
    
    results = await asyncio.gather(*tasks)
    all_messages = [msg for batch in results for msg in batch]
    
    df_log = pd.DataFrame(all_messages)
    output_file = "mortality_analysis_log.csv"
    df_log.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"分析結果已輸出至 {output_file}")

if __name__ == '__main__':
    asyncio.run(main())
