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

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

import httpx

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    http_client=httpx.Client(
        proxy="http://127.0.0.1:7897"   # ← 改成你 Clash Verge 的端口
    )
)

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