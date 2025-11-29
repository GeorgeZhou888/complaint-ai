from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
from docx import Document
import glob

load_dotenv()
# ==================== Railway 专用调试 + 强制检查密钥 ====================
import os
import sys

print("=== [Railway 调试] 正在启动应用，检查环境变量 ===")
key = os.getenv("DASHSCOPE_API_KEY")

if not key:
    print("错误：DASHSCOPE_API_KEY 环境变量未设置或为空！应用无法启动！")
    print("请在 Railway Variables 中正确添加 DASHSCOPE_API_KEY")
    sys.exit(1)  # 直接退出，防止继续运行

print(f"成功读取到 DASHSCOPE_API_KEY！长度: {len(key)} 字符")
print("OpenAI 客户端初始化中...")

# 正式初始化客户端（不再使用本地代理！Railway 不需要）
client = OpenAI(
    api_key=key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

print("OpenAI 客户端初始化成功！")
print("====================================================")
# =====================================================================

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============ 自动加载知识库（所有Word文档）============
def load_all_knowledge():
    text = ""
    for filepath in glob.glob("knowledge_base/*.docx"):
        doc = Document(filepath)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
        text += "\n\n"  # 文档之间空行分隔
    return text

KNOWLEDGE = load_all_knowledge()

# ============ 加载你的专业JSON提示词 ============
with open("system_prompt.json", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT_FULL = json.load(f)[0]["prompt"]

# 安全注入知识库（关键改动！）
if "{knowledge}" in SYSTEM_PROMPT_FULL:
    SYSTEM_PROMPT = SYSTEM_PROMPT_FULL.replace("{knowledge}", KNOWLEDGE)
else:
    SYSTEM_PROMPT = "【以下是完整法律知识库，仅用于你生成投诉信时引用】\n" + KNOWLEDGE + "\n【知识库结束】\n\n" + SYSTEM_PROMPT_FULL

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.get_template("index.html").render({"request": request})

@app.post("/generate")
async def generate(request: Request, user_input: str = Form(...)):
    completion = client.chat.completions.create(
        model="deepseek-v3.2-exp",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        temperature=0.3,
        max_tokens=8192,
        extra_body={"enable_thinking": True},
        stream=True
    )

    full_response = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user_input": user_input,
        "result": full_response
    })