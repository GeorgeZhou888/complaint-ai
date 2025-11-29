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
os.environ["DASHSCOPE_API_KEY"] = "sk-66c90f79d2814119a50639180d2d3b08"  # 临时硬编码

# ==================== 终极调试：打印所有环境变量 + 检查 TEST_VAR ====================
print("="*60)
print(">>> [DEBUG 终极版] 正在启动应用... 打印所有环境变量...")

try:
    all_vars = dict(os.environ)
    print(">>> [DEBUG] --- 所有环境变量开始 ---")
    for k, v in sorted(all_vars.items()):
        # 为了安全，密钥类只显示长度和前后几位
        if 'KEY' in k.upper() or 'TOKEN' in k.upper() or 'PASS' in k.upper():
            if v:
                print(f"{k}: [长度 {len(v)}] {v[:6]}...{v[-4:]}")
            else:
                print(f"{k}: None")
        else:
            print(f"{k}: {v}")
    print(">>> [DEBUG] --- 所有环境变量结束 ---")
except Exception as e:
    print(f">>> [DEBUG] 打印环境变量出错: {e}")

# 检查测试变量
test_var = os.getenv("TEST_VAR")
print(f">>> [DEBUG] TEST_VAR 的值: {test_var}")

# 检查你的真实 key
dash_key = os.getenv("DASHSCOPE_API_KEY")
if not dash_key:
    print(">>> [DEBUG] 错误：DASHSCOPE_API_KEY 未找到！(值为 None)")
    print(">>> [DEBUG] 已跳过 sys.exit() 以继续查看日志")
else:
    print(f">>> [DEBUG] 成功！DASHSCOPE_API_KEY 已找到 (长度: {len(dash_key)})")

# 尝试初始化客户端（无论如何都执行）
try:
    client = OpenAI(
        api_key=dash_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    print(">>> [DEBUG] OpenAI 客户端初始化成功！")
except Exception as e:
    print(f">>> [DEBUG] OpenAI 客户端初始化失败: {e}")

print("="*60)
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