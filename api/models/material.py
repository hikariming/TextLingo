from datetime import datetime
from mongoengine import Document, StringField, IntField, DateTimeField, ObjectIdField

class Material(Document):
    def __init__(self, title, file_type, file_size, file_path, user_id, original_filename=None):
        self.title = title
        self.file_type = file_type
        self.file_size = file_size
        self.file_path = file_path
        self.user_id = user_id
        self.original_filename = original_filename
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            "title": self.title,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_path": self.file_path,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }