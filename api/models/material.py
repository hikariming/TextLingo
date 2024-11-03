from datetime import datetime
from mongoengine import Document, StringField, IntField, DateTimeField, ListField, ReferenceField, CASCADE, BooleanField
from models.material_segment import MaterialSegment

class Material(Document):
    title = StringField(required=True)
    file_type = StringField(required=True)
    file_size = IntField(required=True)
    file_path = StringField(required=True)
    original_file_path = StringField()
    user_id = StringField()
    original_filename = StringField()
    status = StringField(default="pending_segmentation")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    factory_id = StringField()
    segments = ListField(StringField())
    target_language = StringField(default="zh-CN")
    enable_deep_explanation = BooleanField(default=False)
    translation_status = StringField(default="pending")

    meta = {
        'collection': 'materials',
        'indexes': [
            'user_id',
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Material, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),
            "title": self.title,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_path": self.file_path,
            "original_file_path": self.original_file_path,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "factory_id": self.factory_id,
            "target_language": self.target_language,
            "enable_deep_explanation": self.enable_deep_explanation,
            "translation_status": self.translation_status,
            "segments": self.segments,
        }