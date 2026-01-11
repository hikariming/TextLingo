# Production Version

## Step1: Deploy with Docker

```bash
cd docker
docker-compose up -d
```

Access `http://127.0.0.1:3000` in browser

## Step2: Configure Model API Key, Base URL and Model Name in Settings

This project requires LLM and TTS services. There are multiple options available. **Please read the configuration guide carefully 😊**

### 1. **Get LLM API_KEY**:

| Recommended Model | Provider | base_url | Price | Effect |
|:-----|:---------|:---------|:-----|:---------|
| gemini-1.5-pro-002 | [Yunwu API](https://yunwu.zeabur.app/register?aff=TXMB) | https://yunwu.zeabur.app | ¥7 / 1M tokens | 🤩 |
| claude-3-5-sonnet-20240620 | [Yunwu API](https://yunwu.zeabur.app/register?aff=TXMB) | https://yunwu.zeabur.app | ¥10 / 1M tokens | 🤩 |
| gpt-4o | [Yunwu API](https://yunwu.zeabur.app/register?aff=TXMB) | https://yunwu.zeabur.app | ¥7 / 1M tokens | 😃 |

⚠️ Note: Claude, Grok and domestic models like Deepseek are recommended. GPT-4 is not recommended.

<details>
<summary>How to get API key from Yunwu API?</summary>

1. Go to [Yunwu API website](https://yunwu.zeabur.app/register?aff=TXMB)
2. Register an account and top up
3. Create a new key in the API key page
4. Make sure to check `Unlimited quota` and select `Pure AZ 1.5x` channel
</details>

<details>
<summary>Can I use other models?</summary>

- ✅ OAI-Like API interfaces are supported, you can change it in Settings.
- ⚠️ However, other models (especially smaller ones) have weak instruction following capabilities and are prone to errors during translation. Strongly not recommended. If you encounter errors, please switch models.
</details>

Claude 3.5 Sonnet and Deepseek models work well!

Recommend using API from https://yunwu.zeabur.app/ (can use Claude at a low price, super cheap!)

If you pursue stability, you can use openrouter



# Development Version

## Requirements
- Python 3.8+
- Node.js 16+
- MongoDB 4.0+

## I. Backend Deployment

### 1. Install Dependencies
```bash
cd api
pip install -r requirements.txt
```

### 2. Configuration File
Copy the configuration template to create the actual config:
```bash
cp config.example.yml config.yml
```

Edit `config.yml`:
```yaml
mongodb:
  uri: "mongodb://username:password@localhost:27017/dbname?authSource=admin"
  # Modify with your MongoDB connection info

secret_key: "your-secret-key-here" 
# Set a random string as secret key

llm_api_key: "your-openai-api-key-here"
# Enter your API key

llm_base_url: "https://api.wlai.vip/v1"  
# Official API URL: https://api.openai.com/v1
# Third-party API URL depends on provider

llm_model: "claude-3-5-sonnet-20241022"  
# Available models: gpt-4-turbo-preview, gpt-3.5-turbo, etc.
```

### 3. Start Backend
```bash
cd api
python app.py
```

Defaults to `http://localhost:5000`

## II. Frontend Deployment

### 1. Install Dependencies
```bash
cd web

# Using npm
npm install

# Or using pnpm (recommended, faster)
pnpm install

# Or using cnpm (for poor network conditions in China)
cnpm install
```

### 2. Run in Development Environment
```bash
npm run dev
```
Defaults to `http://localhost:3000`

### 3. Production Build
```bash
npm run build
```
Build output in `dist` directory

## III. Important Notes

1. MongoDB Related:
   - Ensure MongoDB service is running
   - Configure database username and password correctly
   - Ensure database port is accessible

2. API Related:
   - Ensure API Key is valid with sufficient quota
   - If using third-party API, ensure service stability

3. Network Related:
   - Check backend CORS configuration if encountering cross-origin issues
   - Ensure frontend and backend ports are not occupied

4. Production Deployment:
   - Recommend using nginx as frontend static resource server
   - Recommend using gunicorn or uwsgi as WSGI server for backend
   - Recommend configuring SSL certificate for HTTPS

## IV. Common Troubleshooting

1. Frontend Cannot Connect to Backend:
   - Check if backend service is running properly
   - Verify frontend API address configuration
   - Check network connection and firewall settings

2. MongoDB Connection Failed:
   - Check MongoDB service status
   - Verify connection string format
   - Confirm user permission configuration

3. API Call Failed:
   - Check API Key configuration
   - Confirm model name is correct
   - Check API quota balance