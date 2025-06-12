# 🚀 Deploy Your AI Admin Interface - Railway Guide

This guide will help you deploy your AI Research Assistant with the admin interface so your colleague can access it remotely to improve prompts and test new flows.

## 🎯 What Your Colleague Will Get

After deployment, your colleague will have access to:
- **🔐 Simple login** - Just enter a password, no technical setup required
- **📝 Visual prompt editor** - Edit all system prompts through a clean web interface
- **🧪 Instant testing** - Test prompt changes with sample data before saving
- **⏰ Version control** - Automatic backups and easy rollback if something goes wrong
- **📊 Organized interface** - All prompts categorized (Router, Search, Analysis, etc.)
- **💾 Immediate effects** - Changes go live in your AI system instantly

## ⚡ Railway Deployment (15 minutes)

**Cost: ~$5-10/month | Easiest option**

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Add admin interface"
   git push origin main
   ```

### Step 2: Set Up Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Sign up with GitHub"
3. Authorize Railway to access your GitHub account

### Step 3: Deploy Your Project

1. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `researcher-prototype` repository

2. **Railway will automatically detect** your project structure and start building

### Step 4: Configure Environment Variables

1. **Go to your project dashboard** on Railway
2. **Click on "Variables" tab**
3. **Add these environment variables**:

   ```bash
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ADMIN_PASSWORD=YourSecurePassword123!
   ADMIN_JWT_SECRET=your_random_secret_key_here
   ```

4. **Generate a secure JWT secret**:
   ```bash
   # Run this on your computer to generate a secure secret:
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Copy the output and use it as your `ADMIN_JWT_SECRET` value.

### Step 5: Wait for Deployment

1. **Monitor the build process** in Railway dashboard
2. **Wait for "Deployed" status** (usually 2-5 minutes)
3. **Your app will be available** at: `https://your-app-name.railway.app`

### Step 6: Test Your Deployment

1. **Test Main App**:
   - Visit: `https://your-app-name.railway.app`
   - Try asking the AI a question
   - Verify it responds correctly

2. **Test Admin Panel**:
   - Visit: `https://your-app-name.railway.app/admin`
   - Enter your admin password
   - You should see the dashboard with prompt categories

3. **Test Prompt Editing**:
   - Click "Edit" on any prompt
   - Make a small change
   - Click "Test" with sample data
   - Save the change
   - Verify the change appears in version history

## 🔗 Share with Your Colleague

Once your tests pass, send this to your colleague:

---

**Subject: Access to AI Prompt Editor**

Hi! I've set up an admin interface so you can easily improve the AI prompts and test new flows. Here's how to use it:

### 🔗 Access Information
- **Main AI Chat**: `https://your-app-name.railway.app`
- **Admin Panel**: `https://your-app-name.railway.app/admin`
- **Password**: `[the password you set as ADMIN_PASSWORD]`

### 📋 How to Edit Prompts

1. **Login**: Go to the admin panel URL and enter the password
2. **Browse**: You'll see all prompts organized by category:
   - 🚦 **Router** - Directs conversations to the right module
   - 🔍 **Search** - Web search functionality
   - 🔬 **Analysis** - Data analysis and problem solving
   - 🔗 **Integrator** - Combines information from multiple sources
   - 💬 **Response** - Formats the final answers
   - 📚 **Research** - Autonomous research features

3. **Edit**: Click "Edit" on any prompt you want to improve
4. **Test**: Use the test panel to see how your changes work with sample data
5. **Save**: Click "Save" when you're happy with the changes

### 🛡️ Safety Features
- ✅ **Auto-backup**: Every change is automatically saved as a backup
- ✅ **Version history**: Click "History" to see all previous versions
- ✅ **Easy rollback**: Restore any previous version if needed
- ✅ **Test first**: Always test changes before saving
- ✅ **Live changes**: Changes go live instantly in the main app

### 💡 Tips for Success
- Start with small changes to get familiar with the interface
- Use the test feature extensively - it shows exactly how prompts will work
- Don't worry about breaking anything - you can always rollback changes
- Focus on one prompt category at a time

**No technical knowledge required - everything is point-and-click!** 🎉

---

## 🛠️ Troubleshooting

### Common Issues

**"Build failed" or deployment errors**:
1. Check that your `backend/app.py` file exists
2. Verify `backend/requirements.txt` is present
3. Make sure you've pushed all files to GitHub

**Admin login not working**:
1. Double-check your `ADMIN_PASSWORD` environment variable
2. Verify `ADMIN_JWT_SECRET` is set
3. Try clearing browser cache/cookies

**App not responding**:
1. Check Railway logs: Go to your project → Deployments → View Logs
2. Verify your `OPENAI_API_KEY` is correct
3. Make sure all environment variables are set

### Getting Help

1. **Check Railway logs**: Project Dashboard → Deployments → View Logs
2. **Verify environment variables**: Project Dashboard → Variables tab
3. **Test locally first** using the local testing commands from your terminal

## 🎉 You're Done!

**Your colleague now has:**
- ✅ Professional web interface to edit AI prompts
- ✅ Real-time testing capabilities
- ✅ Automatic backups and version control
- ✅ Changes that go live instantly in your AI system
- ✅ Zero technical setup required on their end

**Total setup time: 15 minutes**
**Monthly cost: $5-10**
**Colleague experience: User-friendly and professional** 🚀

## 📞 Need Help?

Based on your previous terminal issues, remember:
1. Your `app.py` file is in the `backend/` folder (Railway handles this automatically)
2. Railway will install dependencies and start your app correctly
3. All environment variables must be set in Railway dashboard
4. The admin interface will be available at `/admin` on your deployed URL

Your deployment is now ready to share with your colleague! 