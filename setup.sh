#!/bin/bash

# Daily Activity Tracker - GitHub Setup Script
# This script helps you push your files to GitHub quickly

echo "🚀 Daily Activity Tracker - GitHub Setup"
echo "========================================"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed!"
    echo "Please install from: https://git-scm.com/download/mac"
    echo "Or run: brew install git"
    exit 1
fi

echo "✅ Git is installed"
echo ""

# Get GitHub username
read -p "Enter your GitHub username: " github_user

# Get repository name (default provided)
read -p "Enter repository name [daily-activity-tracker]: " repo_name
repo_name=${repo_name:-daily-activity-tracker}

echo ""
echo "📋 Summary:"
echo "  Username: $github_user"
echo "  Repository: $repo_name"
echo ""

read -p "Is this correct? (y/n) " confirm
if [[ $confirm != [yY] ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🔧 Setting up Git repository..."

# Initialize git if not already
if [ ! -d ".git" ]; then
    git init
    echo "✅ Initialized git repository"
else
    echo "ℹ️  Git repository already exists"
fi

# Add all files
git add .
echo "✅ Added all files"

# Commit
git commit -m "Initial commit - Daily Activity Tracker" 2>/dev/null || echo "ℹ️  No changes to commit"

# Set main branch
git branch -M main
echo "✅ Set main branch"

# Add remote
git remote remove origin 2>/dev/null  # Remove if exists
git remote add origin "https://github.com/$github_user/$repo_name.git"
echo "✅ Added remote origin"

echo ""
echo "📤 Next steps:"
echo ""
echo "1. Go to GitHub.com and create a new PRIVATE repository:"
echo "   https://github.com/new"
echo ""
echo "2. Repository name: $repo_name"
echo "   ☑️ Make it PRIVATE"
echo "   ☐ Don't initialize with README (we have one)"
echo ""
echo "3. After creating the repository, run:"
echo "   git push -u origin main"
echo ""
echo "4. Then go to Streamlit Cloud to deploy:"
echo "   https://share.streamlit.io"
echo ""

read -p "Press Enter to continue..."

echo ""
echo "🔐 Would you like to set up password protection?"
read -p "Set a password? (y/n) " set_password

if [[ $set_password == [yY] ]]; then
    read -s -p "Enter app password: " app_password
    echo ""
    read -s -p "Confirm password: " app_password_confirm
    echo ""
    
    if [[ $app_password == $app_password_confirm ]]; then
        mkdir -p .streamlit
        cat > .streamlit/secrets.toml << EOF
# This file is NOT committed to GitHub
# You'll need to add this in Streamlit Cloud dashboard

[passwords]
app_password = "$app_password"
EOF
        echo "✅ Created secrets.toml"
        echo "⚠️  Remember to add this password in Streamlit Cloud > Settings > Secrets"
    else
        echo "❌ Passwords don't match!"
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📖 See DEPLOYMENT_GUIDE.md for detailed instructions"
