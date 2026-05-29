"""
飞书机器人模块
提供命令处理功能
"""
from typing import Dict, Any, Optional
from app.services.feishu_service import feishu_service
from app.config import Config


class FeishuBot:
    """飞书机器人类"""
    
    def __init__(self):
        self.commands = {
            "help": self.handle_help,
            "status": self.handle_status,
            "你好": self.handle_hello,
        }
    
    async def handle_message(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理收到的消息
        
        Args:
            event: 飞书事件
        
        Returns:
            响应消息内容
        """
        message = event.get("message", {})
        sender = event.get("sender", {})
        
        # 获取消息内容
        message_type = message.get("message_type")
        if message_type != "text":
            return None
        
        # 解析文本消息
        content = message.get("content", "{}")
        import json
        try:
            content_dict = json.loads(content)
            text = content_dict.get("text", "").strip()
        except:
            text = content.strip()
        
        # 获取发送者信息
        sender_id = sender.get("sender_id", {}).get("open_id", "")
        
        # 处理命令
        response = await self.process_command(text, sender_id)
        
        if response:
            # 发送响应消息
            feishu_service.send_text_message(
                receive_id=sender_id,
                content=response,
                receive_id_type="open_id"
            )
        
        return None
    
    async def process_command(self, text: str, sender_id: str) -> Optional[str]:
        """
        处理命令
        
        Args:
            text: 消息文本
            sender_id: 发送者ID
        
        Returns:
            响应文本
        """
        # 检查是否是命令
        text_lower = text.lower()
        
        # 匹配命令
        for cmd, handler in self.commands.items():
            if text_lower.startswith(cmd) or text_lower == cmd:
                return await handler(text, sender_id)
        
        # 默认响应
        return "你好！我是域名管家机器人。发送 \"help\" 查看可用命令。"
    
    async def handle_help(self, text: str, sender_id: str) -> str:
        """处理帮助命令"""
        help_text = """
【域名管家机器人】
可用命令：
- help / 帮助：显示此帮助信息
- status / 状态：查看系统状态
- 你好：问候机器人
        """.strip()
        return help_text
    
    async def handle_status(self, text: str, sender_id: str) -> str:
        """处理状态命令"""
        return "域名管家系统运行正常！"
    
    async def handle_hello(self, text: str, sender_id: str) -> str:
        """处理问候命令"""
        return "你好！有什么可以帮助你的吗？"


# 单例实例
feishu_bot = FeishuBot()

