import json
from _io import BufferedReader

class Database:
    """
    简单的键值对数据库类，使用 JSON 格式进行持久化存储
    """
    def __init__(self, default_dict={}, filename=None, readonly=False):
        """
        初始化数据库
        
        Args:
            default_dict: 默认数据字典
            filename: 数据库文件名
            readonly: 是否只读模式
        """
        self.data: dict = default_dict
        self.readonly: bool = readonly
        self.filename: str | None = filename

    def __getitem__(self, key):
        """通过键获取值"""
        return self.data[key]

    def __setitem__(self, key, value):
        """
        通过键设置值（只读模式下会抛出异常）
        
        Args:
            key: 键
            value: 值
        """
        if self.readonly:
            raise Exception("This database is READ-ONLY.")
        self.data.setdefault(key, value)
        self.data[key] = value

    def save(self, filename: str | None = None):
        """
        将数据保存到 JSON 文件
        
        Args:
            filename: 目标文件名，如果为 None 则使用初始化时的 filename
        """
        # 确定最终使用的文件名
        target_filename = filename if filename is not None else self.filename
        if target_filename is None:
            raise Exception("Please give a filename to save the database.")
        
        # 使用 with 语句自动管理文件句柄，确保资源释放
        try:
            with open(target_filename, "w", encoding="utf-8") as file_obj:
                # ensure_ascii=False 支持中文存储
                json.dump(self.data, file_obj, ensure_ascii=False, indent=2)
        except IOError as e:
            raise Exception(f"Failed to save database: {e}")

    @staticmethod
    def load(filename: str, readonly: bool = False):
        """
        从 JSON 文件加载数据并返回 Database 实例
        
        Args:
            filename: 数据库文件名
            readonly: 是否以只读模式加载
            
        Returns:
            Database 实例
        """
        try:
            with open(filename, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except FileNotFoundError:
            raise Exception(f"文件未找到: {filename}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 解析失败 (文件可能损坏): {e}")
        
        # 创建新实例，数据从文件加载
        obj = Database(default_dict=data, filename=filename, readonly=readonly)
        return obj

def db_terminal(db: Database):
    """
    数据库交互终端，允许直接对数据库进行操作
    
    Args:
        db: Database 实例
    """
    while True:
        exec(input(">>> "))

def load(filename: str, readonly: bool = False):
    """
    加载数据库的便捷函数
    
    Args:
        filename: 数据库文件名
        readonly: 是否只读模式
        
    Returns:
        Database 实例
    """
    return Database.load(filename=filename, readonly=readonly)
