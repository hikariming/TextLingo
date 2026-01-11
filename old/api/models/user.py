from datetime import datetime

class User:
    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at
        }