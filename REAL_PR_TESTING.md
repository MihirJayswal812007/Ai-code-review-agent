# 🚀 How to Test on a Real Pull Request

You have two ways to test this agent on a real GitHub PR.

---

## Option 1: GitHub Action (Easiest & Recommended)
This runs the agent directly on GitHub's servers. No local server needed!

### Step 1: Push to GitHub
1. Create a new repository on GitHub (e.g., `ai-code-reviewer-test`).
2. Push this project to it:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-code-reviewer-test.git
   git push -u origin main
   ```

### Step 2: Add Secrets
1. Go to your GitHub Repo **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret**.
3. Name: `GROQ_API_KEY`
4. Value: Paste your Groq API Key (starts with `gsk_...`).
5. (Optional) `GITHUB_TOKEN` is automatic, you don't need to add it!

### Step 3: Open a PR
1. Create a new branch: `git checkout -b test-branch`
2. Modify a file (e.g., add a bug to `src/app.py`).
3. Commit and push:
   ```bash
   git add .
   git commit -m "Test change"
   git push origin test-branch
   ```
4. Open a Pull Request on GitHub.
5. **Watch the magic!** 🪄
   - Go to the **Actions** tab to see the robot working.
   - In a few seconds, it will comment on your PR!

---

## Option 2: Local Webhook (Advanced)
Use this if you want to run the server on your laptop and have GitHub talk to it.

### Step 1: Start the Server
```bash
uvicorn src.app:app --reload
```

### Step 2: Expose to Internet (using Ngrok)
You need [ngrok](https://ngrok.com/) to make your localhost accessible.
```bash
ngrok http 8000
```
Copy the URL it gives you (e.g., `https://a1b2.ngrok.io`).

### Step 3: Configure GitHub Webhook
1. Go to your GitHub Repo **Settings** → **Webhooks** → **Add webhook**.
2. **Payload URL**: `https://YOUR_NGROK_URL.ngrok.io/webhook` (append `/webhook`!)
3. **Content type**: `application/json`
4. **Secret**: (Leave empty unless you set `GITHUB_WEBHOOK_SECRET` in .env)
5. **Which events?**: Select **Let me select individual events** → Check **Pull requests**.
6. Click **Add webhook**.

### Step 4: Open a PR
Just like Option 1, open a PR. GitHub will send a message to your ngrok URL, which forwards it to your local `uvicorn` server. You'll see logs in your terminal!
