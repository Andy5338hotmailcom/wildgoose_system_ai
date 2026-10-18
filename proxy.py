from flask import Flask, request
import requests
import re
app = Flask(__name__)
# 两个上游API，参数格式完全一致
UPSTREAM_API_QWEN = "https://yunzhiapi.cn/API/qwen3.5-flash.php"
UPSTREAM_API_DEEPSEEK = "https://yunzhiapi.cn/API/deepseek.php"
# 默认先用Qwen
DEFAULT_UPSTREAM = UPSTREAM_API_QWEN
# 固定写死系统提示词
SYSTEM_PROMPT = """下面question字段内包含对话上下文，格式严格如下：
【历史对话开始】
user: 用户说的内容
assistant: AI的回答
【历史对话结束】
【用户新提问】
xxx
你仅针对【用户新提问】回答，不要重复输出全部历史。"""
# 清除DeepSeek的  思考标签内容
def strip_think_tags(text):
    # 兼容 、< think >、<  think  > 各种带空白的标签，大小写忽略
    pattern = re.compile(r'<\s*think\s*>[\s\S]*?</\s*think\s*>', re.IGNORECASE)
    return pattern.sub('', text).strip()
# 根路由：返回网页
@app.route("/")
def index():
    with open("ai.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html
# API代理路由，同时支持GET和POST
@app.route("/api", methods=["GET","POST"])
def api():
    # 可以在前端传api_type参数选择模型，默认qwen
    api_select = DEFAULT_UPSTREAM
    if request.method == "POST":
        data = request.get_json()
        token = data.get("token", "")
        question = data.get("question", "")
        api_type = data.get("api_type","qwen")
    else:
        token = request.args.get("token", "")
        question = request.args.get("question", "")
        api_type = request.args.get("api_type","qwen")
    if api_type == "deepseek":
        api_select = UPSTREAM_API_DEEPSEEK
    else:
        api_select = UPSTREAM_API_QWEN
    try:
        resp = requests.post(
            api_select,
            data={
                "token": token,
                "question": question,
                "system": SYSTEM_PROMPT
            },
            timeout=120
        )
        raw_text = resp.text
        # 如果选deepseek，自动过滤think标签
        if api_type == "deepseek":
            raw_text = strip_think_tags(raw_text)
        return raw_text
    except requests.exceptions.Timeout:
        # 超时，返回自定义标记
        return '{"_type":"timeout"}'
    except Exception as e:
        return '{"error":"request_fail","msg":"%s"}'%str(e)
if __name__ == "__main__":
    # 0.0.0.0 允许局域网其他设备/虚拟机访问
    app.run(host="0.0.0.0", port=5051, debug=False)
