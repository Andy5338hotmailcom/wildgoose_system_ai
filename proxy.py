from flask import Flask, request
import requests
import re
import sys, os

app = Flask(__name__)

UPSTREAM_API_QWEN = "https://yunzhiapi.cn/API/qwen3.5-flash.php"
UPSTREAM_API_DEEPSEEK = "https://yunzhiapi.cn/API/deepseek.php"
UPSTREAM_API_NEW_QWEN = "https://yunzhiapi.cn/API/qwen/index.php"

SYSTEM_PROMPT = """下面question字段内包含对话上下文，格式严格如下：
【历史对话开始】
user: 用户说的内容
assistant: AI的回答
【历史对话结束】
【用户新提问】
xxx
你仅针对【用户新提问】回答，不要重复输出全部历史。"""

NEW_MODEL_LIST = ["qwen3.7-plus", "qwen3.8-max", "qwen3.8-omni-flash"]

def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.abspath(sys._MEIPASS)
    else:
        return os.path.abspath(".")

def strip_think_tags(text):
    pattern = re.compile(r'<\s*think\s*>[\s\S]*?</\s*think\s*>', re.IGNORECASE)
    return pattern.sub('', text).strip()

@app.route("/")
def index():
    base = get_base_path()
    html_path = os.path.join(base, "ai.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html

@app.route("/api", methods=["POST"])
def api():
    data = request.get_json()
    user_token = data.get("token")
    msg = data.get("msg", "")
    model = data.get("model")
    uid = data.get("uid", "")
    delet = data.get("delet", "")

    if model in NEW_MODEL_LIST:
        params = {
            "token": user_token,
            "mag": msg,
            "model": model,
            "uid": uid,
            "think": "auto",
            "type": "text"
        }
        if delet:
            params["delet"] = delet
        resp = requests.post(UPSTREAM_API_NEW_QWEN, data=params, timeout=120)
        result_text = resp.text.strip()
        return {"content": result_text}
    else:
        if model == "qwen3.5-flash":
            upstream = UPSTREAM_API_QWEN
        elif model == "deepseek":
            upstream = UPSTREAM_API_DEEPSEEK
        else:
            return {"content": "错误：未知模型"}

        history = data.get("history", "")
        full_msg = SYSTEM_PROMPT + "\n" + history + "\n【用户新提问】\n" + msg
        params = {
            "token": user_token,
            "mag": full_msg,
            "model": model,
            "uid": uid,
            "type": "text"
        }
        resp = requests.post(upstream, data=params, timeout=120)
        result_text = resp.text.strip()
        if model == "deepseek":
            result_text = strip_think_tags(result_text)
        return {"content": result_text}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
