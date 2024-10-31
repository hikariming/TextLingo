from datetime import datetime

class Material:
    def __init__(self, title, content, file_type, file_size, user_id):
        self.title = title
        self.content = content
        self.file_type = file_type
        self.file_size = file_size
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }