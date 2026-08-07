from zai import ZhipuAiClient as _Client
from database import Database

DEFAULT_MODEL = "GLM-4-Flash-250414"

class Agent:
    """
    AI 智能体类，封装了与 Zhipu AI 模型交互的基本功能
    
    支持的功能：
    - 发送消息并获取 AI 回复
    - 管理对话历史记录
    - 自动裁剪过长的历史以防止 Token 超限
    - 保存和加载 Agent 状态
    """
    
    def __init__(self, api_key: str, filename: str = "", prompt: str = "", 
                 model: str = DEFAULT_MODEL, temp: float = 0.6, 
                 max_tokens: int = 1000, history: list | None = None, 
                 max_history_len: int | None = None) -> None:
        """
        初始化 Agent 实例
        
        Args:
            api_key: Zhipu AI 的 API 密钥
            filename: 用于保存状态的文件名（可选）
            prompt: 系统/角色提示词，定义 Agent 的身份和行为
            model: 使用的模型名称，默认为 GLM-4-Flash-250414
            temp: 温度参数，控制回复的随机性（0.0-1.0），越高越随机
            max_tokens: 生成回复的最大 Token 数
            history: 初始对话历史列表（可选），格式为 [{"role": "user/assistant/system", "content": "..."}]
            max_history_len: 历史记录最大长度，超过后会自动裁剪（防止 Token 超限）
        """
        self.filename = filename
        self.prompt = prompt
        self.api_key = api_key
        self.model = model
        self.temp = temp
        self.max_tokens = max_tokens
        # 新增：最大历史记录长度限制，防止 Token 超限
        self.max_history_len = max_history_len
        
        # 初始化对话历史
        if history is None:
            self.history = [{"role": "system", "content": prompt}]
        else:
            self.history = history
        
        # 创建 AI 客户端
        self.client = _Client(api_key=self.api_key)
        self.length = len(self.history)

    def _trim_history(self):
        """
        内部方法：根据 max_history_len 裁剪历史记录
        
        保留第一条 system 消息，然后截取最后 N 条消息，确保总长度不超过限制
        """
        if self.max_history_len is not None and len(self.history) > self.max_history_len:
            # 保留第一条 system 消息，截断后面的
            system_msg = self.history[0]
            self.history = [system_msg] + self.history[-(self.max_history_len - 1):]
            self.length = len(self.history)

    def send_msg(self, msg: str = "……", role: str = "user", 
                 temp: float | None = None, max_tokens: int | None = None, 
                 retry: int = 3) -> str:
        """
        发送消息给 AI 并获取回复
        
        Args:
            msg: 要发送的消息内容
            role: 消息角色，可选值：user(用户) / assistant(助手) / system(系统)
            temp: 本次请求的温度参数（可选），覆盖实例默认值
            max_tokens: 本次请求的最大 Token 数（可选），覆盖实例默认值
            retry: 失败重试次数，默认为 3 次
            
        Returns:
            AI 的回复内容字符串
            
        Raises:
            Exception: 当重试耗尽后仍无法获取回复时抛出异常
        """
        # 使用默认值（如果未提供）
        if temp is None: 
            temp = self.temp
        if max_tokens is None: 
            max_tokens = self.max_tokens
        
        # 将用户消息添加到历史记录
        self.history.append({"role": role, "content": msg})
        
        # 如果是助手消息，直接返回空（不需要调用 API）
        if role == "assistant":
            self.length = len(self.history)
            return ""
        
        # 发送前检查并裁剪历史记录
        self._trim_history()

        # 新增：异常重试机制
        last_error = None
        for attempt in range(retry):
            try:
                # 调用 Zhipu AI API
                res = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    temperature=temp,
                    max_tokens=max_tokens
                )
                # 提取 AI 回复
                ai_res: str = res.choices[0].message.content  # type: ignore
                
                # 将 AI 回复添加到历史记录
                self.history.append({"role": "assistant", "content": ai_res})
                self.length = len(self.history)
                return ai_res
            except Exception as e:
                last_error = e
                # 可以在这里添加日志记录
                continue
        
        # 重试失败后抛出异常
        raise Exception(f"API 请求失败，已重试 {retry} 次。错误信息: {last_error}")

    def format_history(self, user: str = "你", assistant: str = "AI", 
                      prompt: str = ": ", line_sep: str = "\n\n", l: int = 0):
        """
        格式化输出对话历史
        
        Args:
            user: 用户角色的显示名称
            assistant: 助手角色的显示名称
            prompt: 角色名称和内容之间的分隔符
            line_sep: 每条消息之间的分隔符
            l: 从历史记录的第几条开始格式化（0 表示从头开始）
            
        Returns:
            格式化后的对话历史字符串
        """
        output = ""
        # 遍历历史记录并格式化
        for msg in self.history[l:]:
            if msg["role"] == "user":
                output += user + prompt + msg["content"] + line_sep
            elif msg["role"] == "assistant":
                output += assistant + prompt + msg["content"] + line_sep
            elif msg["role"] == "system":
                # 系统消息不显示在格式化输出中
                continue
        
        # 移除末尾多余的行分隔符
        if output.endswith(line_sep):
            output = output[:-len(line_sep)]
        return output

    def __getitem__(self, key):
        """
        通过索引获取历史记录中的某条消息
        
        Args:
            key: 索引值
            
        Returns:
            历史记录中的消息字典 {"role": "...", "content": "..."}
        """
        return self.history[key]

    def save(self, filename: str | None = None):
        """
        保存 Agent 的当前状态到文件
        
        Args:
            filename: 目标文件名，如果为 None 则使用初始化时的 filename
        """
        db = Database(filename=filename if filename else self.filename)
        db["filename"] = self.filename
        db["prompt"] = self.prompt
        db["api_key"] = self.api_key
        db["model"] = self.model
        db["history"] = self.history
        db["temp"] = self.temp
        db["max_tokens"] = self.max_tokens
        db["max_history_len"] = self.max_history_len  # 新增字段
        db["length"] = self.length
        db.save()

    @staticmethod
    def load(filename: str):
        """
        从文件加载 Agent 状态并返回新实例
        
        Args:
            filename: 数据库文件名
            
        Returns:
            加载了状态的 Agent 实例
        """
        config = Database.load(filename=filename)
        agent = Agent(
            history=config["history"],
            filename=config["filename"],
            max_tokens=config["max_tokens"],
            api_key=config["api_key"],
            model=config["model"],
            prompt=config["prompt"],
            temp=config["temp"],
            max_history_len=config.data.get("max_history_len")  # 兼容旧数据
        )
        return agent
