# EzAgent - README
## 仓库说明
这是一个使用了ZhipuAI的API的LLMpython库。只需要输入模型名称和API Key就可以立即生成回答，操作极其简单

## 使用实例
``` python
from ezagent import Agent

my_agent = Agent(api_key="...", model="...")
print("回答：" + my_agent.send_msg(input("问题：")))
```
