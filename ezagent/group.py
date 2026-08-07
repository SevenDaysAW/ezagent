from typing import List, Dict, Optional
from agent import Agent
from database import Database
import random

class ChatGroup:
    """多Agent群聊类，实现多个Agent之间的群组对话"""
    
    def __init__(self, agents: List[Agent], group_name: str = "默认群组"):
        """
        初始化群聊
        
        Args:
            agents: 参与群聊的Agent列表
            group_name: 群组名称
        """
        self.agents = agents
        self.group_name = group_name
        self.message_history: List[Dict] = []
        self.round_count = 0
        
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """根据名称获取Agent"""
        for agent in self.agents:
            if hasattr(agent, 'prompt') and name in agent.prompt:
                return agent
        return None
    
    def broadcast_message(self, sender: Agent, message: str) -> None:
        """
        发送者向群组广播消息，其他Agent接收并添加到各自的历史记录
        
        Args:
            sender: 发送消息的Agent
            message: 消息内容
        """
        self.message_history.append({
            "round": self.round_count,
            "sender": sender.prompt[:20] + "..." if len(sender.prompt) > 20 else sender.prompt,
            "content": message
        })
        
        for agent in self.agents:
            if agent != sender:
                agent.send_msg(message, role="user")
    
    def get_response(self, agent: Agent, **kwargs) -> str:
        """
        获取指定Agent的回复
        
        Args:
            agent: 要回复的Agent
            **kwargs: 传递给send_msg的额外参数
            
        Returns:
            Agent的回复内容
        """
        response = agent.send_msg(**kwargs)
        
        self.message_history.append({
            "round": self.round_count,
            "sender": agent.prompt[:20] + "..." if len(agent.prompt) > 20 else agent.prompt,
            "content": response
        })
        
        return response
    
    def chat_round(self, starter: Optional[Agent] = None, max_agents: Optional[int] = None, skip_check: bool = False, **kwargs) -> List[Dict]:
        """
        执行一轮群聊
        
        Args:
            starter: 开启对话的Agent，如果为None则随机选择
            max_agents: 本轮参与对话的最大Agent数，如果为None则所有Agent都参与
            skip_check: 是否跳过回答检查（如果为True，所有被点名的Agent强制回答）
            **kwargs: 传递给send_msg的额外参数
            
        Returns:
            本轮对话的所有消息记录
        """
        round_messages = []
        self.round_count += 1
        
        if starter is None:
            starter = random.choice(self.agents)
        
        if max_agents is not None and max_agents < len(self.agents):
            participants = random.sample(self.agents, max_agents)
            if starter not in participants:
                participants[0] = starter
        else:
            participants = self.agents[:]
        
        first_response = self.get_response(starter, msg="请开始一个话题", **kwargs)
        round_messages.append({
            "agent": starter.prompt[:20] + "..." if len(starter.prompt) > 20 else starter.prompt,
            "message": first_response
        })
        
        for agent in participants:
            if agent != starter:
                agent.send_msg(first_response, role="user")
        
        for agent in participants:
            if agent != starter:
                # 新增：智能回答检查
                should_respond = True
                if not skip_check:
                    should_respond = self._check_should_respond(agent)
                
                if should_respond:
                    response = self.get_response(agent, **kwargs)
                    round_messages.append({
                        "agent": agent.prompt[:20] + "..." if len(agent.prompt) > 20 else agent.prompt,
                        "message": response
                    })
                    
                    # 新增：将回复内容广播给后续参与者，以便检查是否被@或需要回应
                    next_agent_found = False
                    for next_agent in participants:
                        if next_agent == agent:
                            next_agent_found = True
                        elif next_agent_found:
                            next_agent.send_msg(response, role="user")
                else:
                    # 记录跳过状态（可选）
                    round_messages.append({
                        "agent": agent.prompt[:20] + "..." if len(agent.prompt) > 20 else agent.prompt,
                        "message": "[跳过本轮发言]"
                    })

        return round_messages

    def _check_should_respond(self, agent: Agent, **kwargs) -> bool:
        """
        检查Agent是否应该回答（内部方法）
        
        Args:
            agent: 待检查的Agent
            **kwargs: 额外参数
            
        Returns:
            bool: 是否应该回答
        """
        check_prompt = (
            "你当前处于一个群聊中。根据最近的对话记录，判断你是否需要发表意见。\n"
            "判断标准（满足其一即可）：\n"
            "1. 有人直接@了你（或者直接叫了你的名字/身份）。\n"
            "2. 对话内容与你的专业领域或设定角色高度相关，你有强烈的表达欲。\n"
            "3. 对话中有明显的误解或事实错误，你需要纠正。\n"
            "\n"
            "如果你认为不需要回答，请只回复 'SKIP'（大写，不要包含任何其他内容）。\n"
            "如果你认为需要回答，请简述你的回复意图（不超过20字），例如：'同意并补充' 或 '提出反对'。"
        )
        
        try:
            # 获取判断结果
            decision = agent.send_msg(msg=check_prompt, **kwargs)
            
            if decision.strip().upper() == "SKIP":
                return False
            else:
                return True
        except Exception:
            # 如果检查出错，默认回答
            return True
    
    def continuous_chat(self, rounds: int, **kwargs) -> List[List[Dict]]:
        """
        连续多轮群聊
        
        Args:
            rounds: 对话轮数
            **kwargs: 传递给chat_round的额外参数
            
        Returns:
            每轮对话的消息记录列表
        """
        all_rounds = []
        for _ in range(rounds):
            round_messages = self.chat_round(**kwargs)
            all_rounds.append(round_messages)
        return all_rounds
    
    def targeted_chat(self, initiator: Agent, target: Agent, topic: str, turns: int = 3, **kwargs) -> List[Dict]:
        """
        两个Agent之间的定向对话（私聊模式）
        
        Args:
            initiator: 发起对话的Agent
            target: 目标Agent
            topic: 对话主题
            turns: 对话轮次
            **kwargs: 传递给send_msg的额外参数
            
        Returns:
            对话消息记录
        """
        messages = []
        current_agent = initiator
        
        for i in range(turns):
            if i == 0:
                response = self.get_response(current_agent, msg=topic, **kwargs)
            else:
                response = self.get_response(current_agent, **kwargs)
            
            messages.append({
                "agent": current_agent.prompt[:20] + "..." if len(current_agent.prompt) > 20 else current_agent.prompt,
                "message": response
            })
            
            current_agent = target if current_agent == initiator else initiator
            current_agent.send_msg(response, role="user")
        
        return messages
    
    def discussion(self, topic: str, moderator: Optional[Agent] = None, rounds: int = 2, **kwargs) -> Dict:
        """
        围绕特定主题的讨论
        
        Args:
            topic: 讨论主题
            moderator: 主持人Agent（可选）
            rounds: 讨论轮次
            **kwargs: 传递给send_msg的额外参数
            
        Returns:
            讨论结果字典，包含所有Agent的观点和总结
        """
        discussion_data = {
            "topic": topic,
            "moderator": moderator.prompt[:20] if moderator else "无",
            "rounds": rounds,
            "agent_views": {},
            "summary": ""
        }
        
        all_views = []
        
        for round_num in range(rounds):
            self.round_count += 1
            
            for agent in self.agents:
                if agent == moderator:
                    continue
                
                if round_num == 0:
                    response = self.get_response(agent, msg=f"请围绕主题'{topic}'发表你的观点", **kwargs)
                else:
                    response = self.get_response(agent, msg="请继续讨论或回应其他人的观点", **kwargs)
                
                if agent.prompt not in discussion_data["agent_views"]:
                    discussion_data["agent_views"][agent.prompt] = []
                discussion_data["agent_views"][agent.prompt].append(response)
                all_views.append(f"{agent.prompt[:30]}: {response}")
        
        if moderator:
            summary_prompt = "以下是各位成员的讨论内容:\n" + "\n".join(all_views) + f"\n请总结关于'{topic}'的讨论结果。"
            discussion_data["summary"] = self.get_response(moderator, msg=summary_prompt, **kwargs)
        else:
            discussion_data["summary"] = "讨论结束"
        
        return discussion_data
    
    def get_formatted_history(self, user: str = "用户", assistant: str = "助手", 
                            prompt: str = ": ", line_sep: str = "\n\n") -> str:
        """
        获取格式化的群组对话历史
        
        Args:
            user: 用户标签
            assistant: 助手标签
            prompt: 提示符
            line_sep: 行分隔符
            
        Returns:
            格式化的对话历史字符串
        """
        output = f"=== {self.group_name} 群聊历史 ===\n\n"
        output += f"总轮次: {self.round_count}\n\n"
        
        for msg in self.message_history:
            output += f"[轮次 {msg['round']}] {msg['sender']}{prompt}{msg['content']}{line_sep}"
        
        return output
    
    def get_agents_info(self) -> List[Dict]:
        """
        获取所有Agent的信息
        
        Returns:
            Agent信息列表
        """
        info_list = []
        for i, agent in enumerate(self.agents):
            info_list.append({
                "index": i,
                "prompt": agent.prompt,
                "model": agent.model,
                "history_length": len(agent.history),
                "temperature": agent.temp,
                "max_tokens": agent.max_tokens
            })
        return info_list
    
    def save_group(self, filename: str) -> None:
        """
        保存群组状态到文件
        
        Args:
            filename: 保存的文件名
        """
        group_data = {
            "group_name": self.group_name,
            "message_history": self.message_history,
            "round_count": self.round_count,
            "agents_info": self.get_agents_info()
        }
        
        db = Database(default_dict=group_data, filename=filename)
        db.save(filename=filename)
    
    @staticmethod
    def load_group(filename: str, agents: List[Agent]) -> 'ChatGroup':
        """
        从文件加载群组状态
        
        Args:
            filename: 文件名
            agents: Agent列表（需要与保存时的Agent顺序一致）
            
        Returns:
            恢复的ChatGroup实例
        """
        config = Database.load(filename=filename)
        
        group = ChatGroup(agents=agents, group_name=config["group_name"])
        group.message_history = config["message_history"]
        group.round_count = config["round_count"]
        
        return group
    
    def clear_history(self, keep_system_prompt: bool = True) -> None:
        """
        清空所有Agent的对话历史
        
        Args:
            keep_system_prompt: 是否保留系统提示词
        """
        for agent in self.agents:
            if keep_system_prompt:
                agent.history = [{"role": "system", "content": agent.prompt}]
            else:
                agent.history = []
            agent.length = len(agent.history)
    
    def add_agent(self, agent: Agent) -> None:
        """向群组添加新Agent"""
        if agent not in self.agents:
            self.agents.append(agent)
    
    def remove_agent(self, agent: Agent) -> bool:
        """
        从群组移除Agent
        
        Returns:
            是否成功移除
        """
        if agent in self.agents and len(self.agents) > 1:
            self.agents.remove(agent)
            return True
        return False
    
    def __len__(self) -> int:
        """返回群组中Agent的数量"""
        return len(self.agents)
    
    def __repr__(self) -> str:
        """返回群组的字符串表示"""
        return f"ChatGroup(name='{self.group_name}', agents={len(self.agents)}, rounds={self.round_count})"
