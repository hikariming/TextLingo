from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, ListField, ReferenceField

class MaterialsFactory(Document):
    name = StringField(required=True)
    description = StringField()
    user_id = StringField(required=True)
    materials = ListField(ReferenceField('Material'))
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'materials_factories'}
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(MaterialsFactory, self).save(*args, **kwargs)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "materials": [str(material.id) for material in self.materials],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }