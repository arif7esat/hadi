# 🚀 AutoCommit Pro

**Intelligent Auto-Commit and Push System with AI-Powered Commit Messages**

Never lose your code again! AutoCommit Pro is an advanced automated git management system designed to protect your code against system crashes. With AI-powered commit messages, real-time file monitoring, and intelligent batching, it ensures your projects are continuously and safely backed up.

## ✨ Features

### 🤖 AI-Powered Commit Messages
- **Google Gemini**, **OpenAI GPT-4**, and **Anthropic Claude** support
- Multi-language commit messages (Turkish & English)
- Intelligent code analysis with descriptive and educational messages
- Smart commit history that tells the story of your development

### 📁 Smart File Monitoring
- Real-time file change detection
- Intelligent filtering (code files only)
- Performance optimization with debouncing
- Support for multiple file types

### 🔄 Automatic Git Operations
- Automatic add, commit, and push workflow
- Efficient batching system
- Error tolerance and retry mechanisms
- Manual intervention options

### 📊 Advanced Monitoring and Reporting
- Detailed logging system
- Performance metrics
- Error analysis and reporting
- Real-time dashboard

### ⚙️ Flexible Configuration
- JSON-based configuration
- Environment variables support
- Project-specific customization
- Easy setup wizard

## 🛠️ Installation

### Prerequisites
```bash
# Python 3.8+ required
python --version

# Git installed and configured
git --version
git config user.name
git config user.email
```

### 🚀 Super Easy Setup (Just 2 Steps!)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/autocommit-pro.git
cd autocommit-pro

# 2. Run and follow the setup wizard!
python main.py --start
```

**That's it!** The system will automatically:
- ✅ Install all dependencies
- ✅ Initialize git repository (if needed)
- ✅ Guide you through API key setup (just paste your key!)
- ✅ Start monitoring your project

**No manual installation, no complex setup!** 🎉

### **🤖 AI Setup is Super Easy:**
1. **Click the link** that opens automatically
2. **Get your FREE API key** (30 seconds)
3. **Paste it** when prompted
4. **Done!** AI generates smart commit messages

## 🚀 Usage

### Basic Commands

```bash
# Start automatic monitoring
python main.py --start

# Interactive setup
python main.py --interactive

# Check system status
python main.py --status

# Manual commit with AI message
python main.py --commit "Custom commit message"

# Manual push
python main.py --push

# Monitor specific directory
python main.py --directory /path/to/project --start
```

### Easy Script Interface

```bash
# Use the convenient script
./run.sh

# Or install globally for any project
./install.sh
```

## ⚙️ Configuration

### Basic Settings (`config.json`)

```json
{
  "system": {
    "monitoring_interval": 30,
    "max_commit_frequency": 300,
    "auto_push_enabled": true
  },
  "ai_commit": {
    "enabled": true,
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "api_key": "",
    "preferred_language": "en"
  },
  "monitoring": {
    "exclude_directories": [
      ".git", "__pycache__", "node_modules"
    ],
    "file_extensions": [
      ".py", ".js", ".ts", ".html", ".css", ".md"
    ]
  }
}
```

### Environment Variables

```bash
# Copy env.example to .env and configure
cp env.example .env

# Required
GEMINI_API_KEY=your_api_key

# Optional
AUTO_PUSH_ENABLED=true
MAX_COMMIT_FREQUENCY=300
```

## 🎯 Use Cases

### 1. **Development Environment Continuous Backup**
```bash
cd /path/to/your/project
python /path/to/autocommit/main.py --start
```

### 2. **Server Environment Auto-Backup**
```bash
# Add as cron job
@reboot cd /path/to/project && python /path/to/autocommit/main.py --start > autocommit.log 2>&1 &
```

### 3. **Multi-Project Monitoring**
```bash
# Each project with separate configuration
python main.py --config project1.json --directory /path/to/project1 --start &
python main.py --config project2.json --directory /path/to/project2 --start &
```

## 🤖 AI Commit Message Examples

AutoCommit Pro generates intelligent, educational commit messages:

```
feat: Add user authentication system

- Implement JWT token-based authentication
- Create login and logout endpoints  
- Add middleware for route protection
- Use bcrypt for secure password hashing

This change enables users to securely access the system
and improves session management reliability.
```

```
fix: Resolve API response format inconsistency

- Apply standard response format across all endpoints
- Add missing status codes in error handling
- Fix Turkish character encoding in JSON responses

This fix makes data exchange between frontend and backend
more reliable and consistent.
```

## 📊 Performance & Statistics

### System Metrics
- **File Monitoring**: ~1000 files/second
- **Commit Time**: Average 2-3 seconds
- **AI Message Generation**: 3-5 seconds
- **Memory Usage**: ~50-100MB

### Customizable Limits
```json
{
  "system": {
    "max_commit_frequency": 300,
    "monitoring_interval": 30,
    "batch_size": 10
  }
}
```

## 🚨 Error Management

### Automatic Recovery
- Network connection retry on failure
- Smart git conflict resolution
- API rate limit handling with backoff
- Resource scaling on system constraints

### Error Notifications
```json
{
  "notifications": {
    "enabled": true,
    "methods": ["console", "system"],
    "email": {
      "enabled": false,
      "recipients": ["admin@example.com"]
    }
  }
}
```

## 🔒 Security

### API Key Security
```bash
# Use environment variables (recommended)
export GEMINI_API_KEY="your-key"

# Or system environment
echo 'export GEMINI_API_KEY="your-key"' >> ~/.zshrc
```

### Repository Security
- Automatic `.gitignore` management
- Prevention of sensitive file commits
- API key exclusion from logs

## 🛠️ Troubleshooting

### Common Issues

**Problem**: Git repository not found
```bash
# Solution
git init
git remote add origin https://github.com/username/repo.git
```

**Problem**: Invalid AI API key
```bash
# Solution - verify your API key
python main.py --setup
```

**Problem**: File monitoring not working
```bash
# Solution - check permissions
chmod +r -R /path/to/project
```

### Debug Mode
```bash
# Detailed error analysis
python main.py --verbose --start
```

### Log Analysis
```bash
# Check error logs
cat logs/error.log

# JSON format for detailed analysis
cat logs/logs.json | grep '"level": "ERROR"'
```

## 🌟 Getting Started

1. **Clone**: `git clone https://github.com/YOUR_USERNAME/autocommit-pro.git`
2. **Run**: `python main.py --start`
3. **Follow**: The setup wizard will guide you through everything!

**That's literally it!** 🎉

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini for powerful AI capabilities
- OpenAI and Anthropic for alternative AI options
- Git community for version control excellence
- Python ecosystem for robust development tools
- All contributors and users

---

**AutoCommit Pro** - Never lose your code again! 🚀✨

*"Even if the system crashes, I can access my code from the repository."*