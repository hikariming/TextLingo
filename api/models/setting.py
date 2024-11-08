from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, DictField

class Setting(Document):
    """系统设置
    key: 配置键名
    value: 配置值
    description: 配置说明
    """
    key = StringField(required=True, unique=True)
    value = StringField(required=True)
    description = StringField()
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'settings',
        'indexes': [
            'key',  # 为key字段创建唯一索引
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Setting, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def get_setting(cls, key, default=None):
        """获取配置值"""
        setting = cls.objects(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_setting(cls, key, value, description=None):
        """设置配置值"""
        setting = cls.objects(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.save()
        else:
            setting = cls(key=key, value=value, description=description)
            setting.save()
        return setting