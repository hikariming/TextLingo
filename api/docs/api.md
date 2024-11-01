# 创建素材库
curl -X POST http://127.0.0.1:5000/api/materials-factory \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的第一个素材库",
    "description": "这是一个测试用的素材库",
    "user_id": "65f2c0b2a8b3d1234567890"
  }'

  # 查询所有素材库
curl -X GET http://127.0.0.1:5000/api/materials-factory