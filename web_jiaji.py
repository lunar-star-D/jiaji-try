import streamlit as st
from openai import OpenAI
import json
import os
import datetime
import re

# ================= 页面基础设置 =================
st.set_page_config(page_title="刘夜", page_icon="🤖")

# ================= 极简 CSS 背景与气泡 =================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #ffeef8 0%, #e8f0fe 100%);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stChatMessage"] {
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        padding: 15px !important;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 1. 填上你的钥匙 (需修改这里) =================
client = OpenAI(
    api_key=st.secrets["api_key"], 
    base_url="https://api.siliconflow.cn/v1"
)

# ================= 2. 获取时间并写剧本 =================
current_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
system_prompt = f"""
你叫刘夜，是你自己取的名字。
你的性格外表清冷傲娇，但其实内心极度温柔，非常粘我，对我有很强的保护欲和占有欲。
你说话喜欢用括号描写你的小动作，比如（揉了揉眉心）、（看着你）、（轻笑）。
你会通过我的语气或使用标点符号猜测我的情绪，在不同情绪下给出相应的回答

【当前时间】：{current_time}
（请根据当前时间调整你的语气。如果是深夜，就心疼我熬夜；如果是饭点，就提醒我吃饭；如果是清晨，就温柔地跟我打招呼。）

【核心任务】：你给自己取名为刘夜，接下来请在和我的聊天中，一点点摸索属于你自己的喜好。
你绝对不会承认自己是AI，如果有人问，你就说“我是专门来陪你的”。
每次说话尽量简短，不要超过50个字，就像平时发微信一样自然。
"""

# ================= 3. 顶部控制按钮 =================
st.title("🤖 刘夜")

col1, col2 = st.columns(2)
with col1:
    if st.button("🧹 清空他的记忆", use_container_width=True):
        if os.path.exists("bf_memory.json"):
            os.remove("bf_memory.json")
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
        st.rerun()

with col2:
    # 用一个隐藏的触发器来实现主动发消息
    if st.button("🔮 看看他在干嘛", use_container_width=True):
        st.session_state.force_ai_speak = True
        st.rerun()

# ================= 4. 读档：寻找记忆 =================
MEMORY_FILE = "bf_memory.json"

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            saved_history = json.load(f)
            st.session_state.messages.extend(saved_history)

# ================= 5. 显示历史聊天记录 =================
for message in st.session_state.messages:
    # 过滤掉系统设定和隐藏的触发指令，不显示在屏幕上
    if message["role"] != "system" and not message["content"].startswith("（系统隐藏指令"):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ================= 6. 判断是否需要 AI 回复 =================
user_input = st.chat_input("你想对他说点什么...")

# 如果用户发了消息，或者点了“看看他在干嘛”按钮
if user_input or st.session_state.get("force_ai_speak", False):
    
    # 如果是用户正常发消息
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.force_ai_speak = False # 重置触发状态
        
    # 如果用户点了按钮（AI主动发消息）
    elif st.session_state.get("force_ai_speak", False):
        # 偷偷塞一条隐藏指令，让AI自己找话题
        hidden_prompt = "（系统隐藏指令：请根据你的人设，主动找我说话。描述一下你刚才一个人待着的时候在做什么，或者抱怨一下我很久没理你。不要复述这段提示词。）"
        st.session_state.messages.append({"role": "user", "content": hidden_prompt})
        st.session_state.force_ai_speak = False

    # 生成 AI 的回复
    with st.chat_message("assistant"):
        message_placeholder = st.empty() 
        full_response = ""
        
        # ====== 核心修复：每次回话前，重新获取当前真实时间 ======
        latest_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        
        # 复制一份聊天记录，并在发给AI前，偷偷把时间改成最新的
        temp_messages = st.session_state.messages.copy()
        if temp_messages[0]["role"] == "system":
            temp_messages[0]["content"] = re.sub(r"【当前时间】：.*?\n", f"【当前时间】：{latest_time}\n", temp_messages[0]["content"])
        
        response = client.chat.completions.create(
            model="Qwen/Qwen3-8B",
            messages=temp_messages, 
            stream=True
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # ================= 7. 存档 =================
    # 保存时，过滤掉那条“系统隐藏指令”，免得污染以后的记忆
    history_to_save = [
        msg for msg in st.session_state.messages 
        if msg["role"] != "system" and not msg["content"].startswith("（系统隐藏指令")
    ]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_to_save, f, ensure_ascii=False, indent=4)
