import psycopg2
from docx import Document
import glob

# 连接你的云数据库（已全部填好）
conn = psycopg2.connect(
    host="gp-wz9nky8t9z17ow5c4-master.gpdb.rds.aliyuncs.com",
    port=5432,
    dbname="database1",
    user="database1",
    password="Liang20040424-$",
    sslmode="require"   # ← 这一行一定要有！阿里云强制SSL
)

cur = conn.cursor()

# 创建知识库表（带向量扩展，后面商用可直接开RAG）
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cur.execute("DROP TABLE IF EXISTS knowledge;")
cur.execute("""
    CREATE TABLE knowledge (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        embedding vector(1024)  -- 预留向量列，后面商用秒开
    );
""")

# 导入所有Word法规
for file in glob.glob("knowledge_base/*.docx"):
    doc = Document(file)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    title = os.path.basename(file)
    print(f"正在导入：{title}")
    cur.execute("INSERT INTO knowledge (title, content) VALUES (%s, %s)", (title, text))

conn.commit()
cur.close()
conn.close()
print("所有法规已成功导入云数据库！你的智能体已升级为企业级RAG版！")