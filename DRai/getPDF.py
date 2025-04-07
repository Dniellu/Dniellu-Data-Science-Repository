import os
from datetime import datetime
import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from fpdf import FPDF
import google.generativeai as genai

# 載入環境變數並設定 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro")  # 使用你設定的 Gemini 模型

def get_chinese_font_file() -> str:
    fonts_path = r"C:\Windows\Fonts"
    candidates = ["kaiu.ttf"]
    for font in candidates:
        font_path = os.path.join(fonts_path, font)
        if os.path.exists(font_path):
            print("找到系統中文字型：", font_path)
            return os.path.abspath(font_path)
    print("未在系統中找到候選中文字型檔案。")
    return None

def create_table(pdf: FPDF, df: pd.DataFrame):
    available_width = pdf.w - 2 * pdf.l_margin
    num_columns = len(df.columns)
    col_width = available_width / num_columns
    cell_height = 10

    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("ChineseFont", "", 12)
    for col in df.columns:
        pdf.cell(col_width, cell_height, str(col), border=1, align="C", fill=True)
    pdf.ln(cell_height)

    fill = False
    for index, row in df.iterrows():
        if pdf.get_y() + cell_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_fill_color(200, 200, 200)
            pdf.set_font("ChineseFont", "", 12)
            for col in df.columns:
                pdf.cell(col_width, cell_height, str(col), border=1, align="C", fill=True)
            pdf.ln(cell_height)
        if fill:
            pdf.set_fill_color(230, 240, 255)
        else:
            pdf.set_fill_color(255, 255, 255)
        for item in row:
            pdf.cell(col_width, cell_height, str(item), border=1, align="C", fill=True)
        pdf.ln(cell_height)
        fill = not fill

def parse_markdown_table(markdown_text: str) -> pd.DataFrame:
    lines = markdown_text.strip().splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    table_lines = [line for line in lines if line.startswith("|")]
    if not table_lines:
        return None
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    data = []
    for line in table_lines[2:]:
        row = [cell.strip() for cell in line.strip("|").split("|")]
        if len(row) == len(headers):
            data.append(row)
    df = pd.DataFrame(data, columns=headers)
    return df

def extract_summary_suggestions(text: str) -> str:
    lines = text.strip().splitlines()
    non_table_lines = []
    table_started = False
    for line in lines:
        if line.startswith("|"):
            table_started = True
        elif table_started and not line.startswith("|"):
            table_started = False
        if not table_started and not line.startswith("|"):
            non_table_lines.append(line)
    return "\n".join(non_table_lines).strip()

def generate_pdf(df: pd.DataFrame = None, suggestions: str = None) -> str:
    print("開始生成 PDF")
    pdf = FPDF(format="A4")
    pdf.add_page()

    chinese_font_path = get_chinese_font_file()
    if not chinese_font_path:
        error_msg = "錯誤：無法取得中文字型檔，請先安裝合適的中文字型！"
        print(error_msg)
        return error_msg

    pdf.add_font("ChineseFont", "", chinese_font_path, uni=True)
    pdf.set_font("ChineseFont", "", 12)

    if df is not None:
        create_table(pdf, df)
    if suggestions:
        pdf.ln(10)
        pdf.set_font("ChineseFont", "", 12)
        pdf.multi_cell(0, 10, suggestions)

    pdf_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    print("輸出 PDF 至檔案：", pdf_filename)
    pdf.output(pdf_filename)
    print("PDF 生成完成")
    return pdf_filename

def gradio_handler(csv_file, user_prompt):
    print("進入 gradio_handler")
    if csv_file is not None:
        df = pd.read_csv(csv_file.name)
        total_rows = df.shape[0]
        block_size = 30
        full_response = ""
        all_tables = []
        all_suggestions = []

        for i in range(0, total_rows, block_size):
            block = df.iloc[i:i+block_size]
            block_csv = block.to_csv(index=False)
            prompt = (f"以下是CSV資料第 {i+1} 到 {min(i+block_size, total_rows)} 筆：\n"
                      f"{block_csv}\n\n請根據以下規則進行分析並產出報表：\n{user_prompt}")
            print("處理 prompt：", prompt[:200], "...")

            # 正確使用 generate_content()
            response = model.generate_content([prompt])
            response_text = response.text.strip()
            full_response += f"區塊 {i//block_size+1} 回應：\n{response_text}\n\n"

            table_df = parse_markdown_table(response_text)
            if table_df is not None:
                all_tables.append(table_df)
            summary_text = extract_summary_suggestions(response_text)
            if summary_text:
                all_suggestions.append(summary_text)

        combined_df = pd.concat(all_tables, ignore_index=True) if all_tables else None
        final_suggestion = "\n\n".join(all_suggestions).strip()
        pdf_path = generate_pdf(df=combined_df, suggestions=final_suggestion)
        return full_response, pdf_path
    else:
        prompt = f"未上傳 CSV 檔案，請分析以下指令：\n{user_prompt}"
        response = model.generate_content([prompt])  # ✅修正為正確用法
        response_text = response.text.strip()
        pdf_path = generate_pdf(suggestions=response_text)
        return response_text, pdf_path

default_prompt = """請根據以下規則分析訪問者與美術生之間的對話，並製作報表：

第一步：
請根據對話的內容，將每段對話標記為以下類別之一（可複選）：
- 訪問者提問（訪問者提出問題）
- 美術生回應（美術生回答或分享）
- 技術性描述（涉及技法、工具、媒材等細節）
- 創作理念（描述創作靈感、概念、主題等）
- 情感表達（帶有情感態度的語句，如興奮、挫折等）
- 交流技巧（例如聆聽、反問、引導等對話技巧）

第二步：
統計每個類別出現的次數，整理為一份統計表格，表格第一欄為類別，第二欄為次數。

第三步：
針對本次對話的統計結果，提供分析建議：
- 哪些類別比例較高或較低，可能代表對話的重點或缺乏面向
- 對於教學或訓練目的，應強化或改善哪些溝通技巧或內容呈現

請以 markdown 格式呈現表格與分析，並輸出完整報告摘要至 PDF 中。"""


with gr.Blocks() as demo:
    gr.Markdown("# CSV 美術生面試對話報表分析器")
    with gr.Row():
        csv_input = gr.File(label="上傳 CSV 檔案")
        user_input = gr.Textbox(label="請輸入分析指令", lines=10, value=default_prompt)
    output_text = gr.Textbox(label="AI 回應內容", interactive=False, lines=20)
    output_pdf = gr.File(label="下載 PDF 報表")
    submit_button = gr.Button("生成報表")
    submit_button.click(fn=gradio_handler, inputs=[csv_input, user_input],
                        outputs=[output_text, output_pdf])

demo.launch()
