from flask import Flask, request
import requests
import re
import sys, os
app = Flask(__name__)
# 上游API
UPSTREAM_API_QWEN = "https://yunzhiapi.cn/API/qwen3.5-flash.php"
UPSTREAM_API_DEEPSEEK = "https://yunzhiapi.cn/API/deepseek.php"
UPSTREAM_API_NEW_QWEN = "https://yunzhiapi.cn/API/qwen/index.php"
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
NEW_MODEL_LIST = ["qwen3.7-plus", "qwen3.8-max", "qwen3.8-omni-flash"]

# 获取当前运行目录，识别pyinstaller打包后的 _MEIxxxxxx 临时解压文件夹
def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.abspath(sys._MEIPASS)
    else:
        return os.path.abspath(".")

# 清除DeepSeek的 思考标签内容
def strip_think_tags(text):
    pattern = re.compile(r'<\s*think\s*>[\s\S]*?</\s*think\s*>', re.IGNORECASE)
    return pattern.sub('', text).strip()

# 根路由：返回网页
@app.route("/")
def index():
    html_path = os.path.join(get_base_path(), "ai.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    return html

# API代理路由，同时支持GET和POST
@app.route("/api", methods=["GET","POST"])
def api():
    token = ""
    msg = ""
    model = ""
    uid = ""
    action = ""
    question = ""

    if request.method == "POST":
        data = request.get_json() or {}
        token = data.get("token", "")
        msg = data.get("msg", "")
        question = data.get("question", "")
        model = data.get("model", "qwen")
        uid = data.get("uid", "")
        action = data.get("action", "")
    else:
        token = request.args.get("token", "")
        msg = request.args.get("msg", "")
        question = request.args.get("question", "")
        model = request.args.get("model", "qwen")
        uid = request.args.get("uid", "")
        action = request.args.get("action", "")

    print("==== 收到请求 ====")
    print(f"model:{model}, uid:{uid}, msg:{msg}, action:{action}")
    model_lower = model.lower()

    # 新模型分支：改用GET，和文档示例一致
    if model_lower in NEW_MODEL_LIST:
        params = {
            "token": token,
            "mag": msg,
            "model": model,
            "uid": uid,
            "think": "auto",
            "type": "text"
        }
        if action == "delet":
            params["delet"] = uid
        print("向上游GET参数：", params)
        try:
            resp = requests.get(UPSTREAM_API_NEW_QWEN, params=params, timeout=120)
            print(f"上游返回code:{resp.status_code}, 返回内容:{resp.text}")
            raw_text = resp.text.strip()
            return raw_text
        except requests.exceptions.Timeout:
            return '{"_type":"timeout"}'
        except Exception as e:
            return '{"error":"request_fail","msg":"%s"}'%str(e)

    # 老模型分支：qwen / deepseek
    api_select = DEFAULT_UPSTREAM
    if model_lower == "deepseek":
        api_select = UPSTREAM_API_DEEPSEEK
    elif model_lower == "qwen":
        api_select = UPSTREAM_API_QWEN

    full_question = SYSTEM_PROMPT + "\n" + question
    try:
        resp = requests.post(
            api_select,
            data={
                "token": token,
                "question": full_question,
                "system": SYSTEM_PROMPT
            },
            timeout=120
        )
        raw_text = resp.text
        if model_lower == "deepseek":
            raw_text = strip_think_tags(raw_text)
        return raw_text
    except requests.exceptions.Timeout:
        return '{"_type":"timeout"}'
    except Exception as e:
        return '{"error":"request_fail","msg":"%s"}'%str(e)

if __name__ == "__main__":
    print("Wildgoose AI test software. Testing only.")
    print("Testing Url: http://127.0.0.1:5051")
    app.run(host="0.0.0.0", port=5051, debug=False)
