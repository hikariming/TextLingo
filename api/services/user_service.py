from app import mongo
from models.user import User

class UserService:
    @staticmethod
    def create_user(username, email):
        user = User(username, email)
        mongo.db.users.insert_one(user.to_dict())
        return user
    
    @staticmethod
    def get_user_by_username(username):
        return mongo.db.users.find_one({"username": username})