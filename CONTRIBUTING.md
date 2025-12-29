# Contributing to Pulse

Thanks for your interest in contributing to Pulse! This guide will help you get up and running with our development workflow.

## Getting Started

### Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.9+ and pip  
- **Git** configured with your GitHub account
- Access to team **Linear** workspace
- **Environment credentials** (provided by team lead)

### Repository Setup

We have two main repositories:

```bash
# Frontend
git clone https://github.com/HealthEase-Technologies/pulse-frontend.git
cd pulse-frontend
npm install
cp .env.example .env.local
npm run dev

# Backend  
git clone https://github.com/HealthEase-Technologies/pulse-backend.git
cd pulse-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Verify setup:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

## First Time Git Setup

**IMPORTANT:** When you clone a repository, Git only creates a local `main` branch by default. You need to set up tracking for all remote branches.

### Step-by-Step Setup:

```bash
# 1. Clone the repository (already done above)
git clone https://github.com/HealthEase-Technologies/pulse-frontend.git
cd pulse-frontend

# 2. Check what branches exist remotely
git branch -r
# You'll see: origin/develop, origin/main, origin/staging

# 3. Set up local tracking branches for all remote branches
git checkout -b staging origin/staging
git checkout -b develop origin/develop

# 4. Switch to develop for daily work (this is your main working branch)
git checkout develop
git pull origin develop

# 5. Verify all branches are available locally
git branch
# Should show: * develop, main, staging

# 6. Install dependencies and start development (ignore if already done)
npm install
cp .env.example .env.local
npm run dev
```

### Why This Setup Is Required:

- **Git's default behavior:** Only creates local `main` branch when cloning
- **Remote branches exist** but aren't automatically tracked locally
- **One-time setup:** After this, you can switch branches normally
- **Team workflow:** Everyone needs access to develop/staging branches

### After Setup - Daily Workflow:

```bash
# Always start new work from the latest develop branch
git checkout develop
git pull origin develop
git checkout -b feature/PULSE-XXX-your-feature
```

## Understanding Git Rebase

### What is Rebasing?

Rebasing is the process of moving your feature branch to start from the latest commit on develop. This keeps project history clean and linear.

**Before rebase:**
```
develop:     A---B---C (teammate's new commits)
                \
feature:         D---E (your commits)
```

**After rebase:**
```
develop:     A---B---C
                    \
feature:             D'---E' (your commits moved to latest develop)
```

### Why We Rebase:

#### 1. **Prevents Merge Conflicts**
- Your feature branch includes the latest changes from develop
- Conflicts are resolved on your branch, not in the main codebase
- Cleaner, safer merges when your PR is approved

#### 2. **Maintains Linear History**
- Avoids messy "merge commit bubbles" in project history
- Each commit represents actual feature work
- Easier to understand project evolution and find bugs

#### 3. **Early Integration Testing**
- Your feature code runs with the latest develop changes
- Catches integration issues before creating PR
- Ensures compatibility with recent team changes

#### 4. **Professional Development Practice**
- Standard practice at professional software companies
- Shows respect for project history and team workflow
- Makes code reviews focus on your changes, not merge complexity

### When to Rebase:

#### **NOT immediately after creating branch**
When you first create a feature branch, it's already up-to-date:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/PULSE-123-login
# No rebase needed here - branch is fresh from latest develop
```

#### **Daily Rebase (Recommended)**
Start each day by syncing with team changes:
```bash
# Before continuing work each day:
git checkout develop
git pull origin develop               # Get latest team changes
git checkout feature/PULSE-123-login
git rebase develop                   # Apply team changes to your branch

# If conflicts occur, resolve them, then:
git rebase --continue
```

#### **Before Creating PR (Mandatory)**
Always rebase before submitting your work:
```bash
# When your feature is complete:
git checkout develop
git pull origin develop               # Get absolutely latest changes
git checkout feature/PULSE-123-login
git rebase develop                   # Ensure your branch is current
git push -f origin feature/PULSE-123-login  # Force push after rebase
# Now create your PR - it will merge cleanly
```

### Signs You Need to Rebase:

- **Working on feature for more than 1 day**
- **Know teammates have merged PRs recently**
- **GitHub shows "This branch is X commits behind develop"**
- **Getting merge conflicts when trying to create PR**
- **Your local develop branch has new commits when you `git pull`**

### Handling Rebase Conflicts:

```bash
git rebase develop
# If conflicts occur:

# 1. Git will pause and show conflicted files
# 2. Open conflicted files and resolve conflicts manually
# 3. Remove conflict markers (<<<<<<<, =======, >>>>>>>)
# 4. Stage resolved files:
git add conflicted-file.js

# 5. Continue the rebase:
git rebase --continue

# 6. If more conflicts, repeat steps 2-5
# 7. When complete, force push:
git push -f origin feature/PULSE-123-login
```

### Rebase Best Practices:

```bash
# Always pull develop first
git checkout develop && git pull origin develop

# Then rebase your feature branch
git checkout feature/PULSE-123-login
git rebase develop

# Force push after rebase (rewrites history)
git push -f origin feature/PULSE-123-login

# Never rebase public/shared branches (only your feature branches)
```

## Project Structure

### Frontend (pulse-frontend)
```
app/              # Next.js App Router
components/       # Reusable React components  
lib/             # Utilities & API clients
public/          # Static assets
styles/          # Global styles
utils/           # Helper functions
```

### Backend (pulse-backend)
```
app/
├── auth/            # Authentication logic
├── config/          # Configuration & database
├── images/          # Static Images
├── routers/         # FastAPI route handlers
├── schemas/         # Pydantic models for request/response
├── services/        # Business logic
└── utils/           # Helper functions
main.py              # Application entry point
requirements.txt     # Python dependencies
.env.example         # Environment template
```

## Branch Strategy & Workflow

### Branch Structure
```
main (Production) ← staging (Pre-prod) ← develop (Integration) ← feature/PULSE-XXX
```

### Branch Types & Naming
```bash
feature/PULSE-123-user-authentication    # New features
bugfix/PULSE-124-login-error            # Bug fixes  
hotfix/PULSE-125-critical-security-fix  # Production hotfixes
```

### Complete Daily Workflow

#### 1. **Starting New Work:**
```bash
# Start from latest develop
git checkout develop
git pull origin develop

# Create feature branch with descriptive name
git checkout -b feature/PULSE-XXX-descriptive-name

# Start coding your feature
```

#### 2. **Daily Development (Multiple Days):**
```bash
# Each morning, sync with team changes:
git checkout develop
git pull origin develop               # Get teammate's merged changes
git checkout feature/PULSE-XXX-descriptive-name
git rebase develop                   # Apply their changes to your work

# Continue working, make commits:
git add .
git commit -m "feat: add user authentication logic (PULSE-123)"
git commit -m "feat: add login validation (PULSE-123)"

# Push your progress (first time):
git push -u origin feature/PULSE-XXX-descriptive-name

# Push updates after rebasing:
git push -f origin feature/PULSE-XXX-descriptive-name
```

#### 3. **Final PR Preparation:**
```bash
# Before creating PR, do final sync:
git checkout develop
git pull origin develop               # Get absolutely latest changes
git checkout feature/PULSE-XXX-descriptive-name
git rebase develop                   # Final rebase

# Push final version:
git push -f origin feature/PULSE-XXX-descriptive-name

# Create PR on GitHub:
# Base: develop
# Compare: feature/PULSE-XXX-descriptive-name
```

#### 4. **After PR is Merged:**
```bash
# Clean up local branches:
git checkout develop
git pull origin develop               # Your changes are now in develop
git branch -d feature/PULSE-XXX-descriptive-name  # Delete local feature branch
git push origin --delete feature/PULSE-XXX-descriptive-name  # Delete remote feature branch
```

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(auth): add JWT token validation        # New feature
fix(api): resolve user profile update bug   # Bug fix
docs(readme): update installation steps     # Documentation
style(ui): improve button hover states      # Style/formatting
refactor(db): optimize user query           # Code refactoring
test(auth): add login flow tests            # Testing
chore(deps): update dependencies            # Maintenance
perf(api): improve response time            # Performance improvement
ci(actions): add automated testing         # CI/CD changes
```

**Required format:** `type(scope): description (PULSE-XXX)`

### Commit Message Examples:
```bash
feat(auth): implement JWT authentication (PULSE-123)
fix(ui): resolve login button alignment issue (PULSE-124)
docs(contributing): add detailed rebase explanation (PULSE-125)
refactor(api): simplify user service logic (PULSE-126)
test(auth): add comprehensive login tests (PULSE-127)
```

## Linear Integration

### Issue Workflow
```
Open → In Progress → In Review → Testing → Done
```

### Linking Work to Linear Issues
- **Branch names:** Must include Linear issue number
- **Commit messages:** Include `(PULSE-XXX)` at the end
- **PR titles:** Include Linear issue number
- **PR description:** Use `Closes PULSE-XXX`

### Example Complete Workflow:
```bash
# 1. Get assigned Linear issue PULSE-123
# 2. Create branch with issue number
git checkout -b feature/PULSE-123-user-dashboard

# 3. Make commits with issue reference
git commit -m "feat: add dashboard layout (PULSE-123)"
git commit -m "feat: implement user profile section (PULSE-123)"

# 4. Create PR with title: "feat: User Dashboard Implementation (PULSE-123)"
# 5. PR description includes: "Closes PULSE-123"
```

## Environment Setup

### Frontend (.env.local)
```env
# Cognito Authentication
NEXT_PUBLIC_COGNITO_USER_POOL_ID=your_user_pool_id_here
NEXT_PUBLIC_COGNITO_CLIENT_ID=your_client_id_here

# Application URLs
NEXT_PUBLIC_APP_URL=http://localhost:3000
# NEXT_PUBLIC_APP_URL=https://pulse-so.vercel.app

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_API_URL=https://pulse-backend-so.vercel.app

# Development
NEXT_PUBLIC_DISABLE_ERROR_OVERLAY=true
```

### Backend (.env)
```env
# Application Settings
APP_NAME=Pulse Backend
DEBUG=False
API_V1_STR=/api/v1

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# AWS Cognito Configuration
AWS_REGION=me-central-1
COGNITO_USER_POOL_ID=your_user_pool_id_here
COGNITO_CLIENT_ID=your_client_id_here

# AWS Credentials (for S3 uploads)
# In production, use Vercel environment variables
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
S3_BUCKET_NAME=your-bucket-name

# Security
SECRET_KEY=generate_with_python_secrets_module
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**CRITICAL: Never commit .env files - they're in .gitignore for security**

## Code Standards

### Frontend
- **JavaScript** for all components and logic
- **ESLint + Prettier** - run `npm run lint` before committing
- **Tailwind CSS** for styling - avoid custom CSS
- **Component naming:** PascalCase (e.g., `UserDashboard.js`)
- **File structure:** Use `.js` for components, `.json` for config
- **AWS Cognito** for authentication - follow established patterns

### Backend  
- **PEP 8** Python style guide
- **Type hints** for all function parameters/returns
- **Docstrings** for all public functions/classes
- **FastAPI** conventions - async/await for database operations
- **Supabase** for database operations
- **AWS services** for file storage and authentication

### Pre-commit Checklist
- [ ] Code follows style guidelines
- [ ] All tests pass locally (`npm test` / `pytest`)
- [ ] No console errors in browser
- [ ] Linear issue linked in commit
- [ ] Environment variables updated if needed
- [ ] Rebased with latest develop before pushing

## Pull Request Guidelines

### PR Template
```markdown
## Description
Brief description of changes made

## Linear Issue  
Closes PULSE-XXX

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work)
- [ ] Documentation update

## Testing
- [ ] Tested locally  
- [ ] All tests pass
- [ ] No console errors
- [ ] Works in preview environment
- [ ] Rebased with latest develop

## Screenshots
(if applicable)
```

### Review Process
1. **Automated checks** must pass (GitHub Actions)
2. **At least 1 approval** from relevant team (Frontend/Backend) required
3. **Test in preview environment** (auto-deployed)
4. **Squash and merge** for clean commit history

### For Reviewers
- Test the feature in preview environment  
- Check code style and conventions
- Verify Linear issue is properly linked
- Look for security/performance issues
- Ensure proper error handling
- Check environment variable usage
- Be constructive in feedback

### For PR Authors
- **Always rebase before creating PR**
- Keep PRs focused and small when possible
- Write clear descriptions with screenshots
- Respond promptly to feedback
- Test thoroughly in preview environment

## Deployment

### Automatic Deployments
| Environment | Trigger | URL |
|-------------|---------|-----|
| **Production** | `main` branch | https://pulse-so.vercel.app |
| **Staging** | `staging` branch | https://pulse-frontend-git-staging-healthease-technologies.vercel.app |
| **Development** | `develop` branch | https://pulse-frontend-git-develop-healthease-technologies.vercel.app |
| **Preview** | Any PR | *-git-branch-*.vercel.app |

### Environment Flow
```
feature/PULSE-XXX → develop → staging → main
       ↓              ↓         ↓        ↓
    Preview         Dev     Staging  Production
```

**All deployments are automatic via Vercel when you push/merge.**

### Environment Variables per Deployment
- **Development:** Uses local/development values
- **Staging:** Uses staging-specific credentials
- **Production:** Uses production credentials and URLs

## Troubleshooting

### Common Issues

#### **"Cannot connect to backend"**
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify environment variables
cat .env.local | grep NEXT_PUBLIC_API_URL

# Restart services
npm run dev        # Frontend
uvicorn app.main:app --reload  # Backend
```

#### **"Module not found" errors**
```bash
# Frontend
rm -rf node_modules package-lock.json
npm install

# Backend
pip install -r requirements.txt
```

#### **CORS errors in browser**
1. Check `app/main.py` CORS configuration
2. Verify your local URL is in `allow_origins`
3. Clear browser cache and restart both services

#### **Authentication errors**
1. Verify Cognito configuration in both frontend and backend
2. Check AWS region settings
3. Ensure User Pool and Client IDs match between environments

#### **Rebase conflicts**
```bash
# If rebase conflicts occur:
git rebase develop
# Resolve conflicts in files, then:
git add .
git rebase --continue
# Force push after successful rebase:
git push -f origin feature/PULSE-XXX-name
```

#### **"This branch is X commits behind"**
This means you need to rebase:
```bash
git checkout develop
git pull origin develop
git checkout your-feature-branch
git rebase develop
git push -f origin your-feature-branch
```

### Getting Help

1. **Check this guide** first - most issues are covered here
2. **Search existing GitHub issues** 
3. **Ask in team chat** for quick questions
4. **Create new issue** for bugs/feature requests
5. **Tag @Huzaifa785** for urgent blockers
6. **Check Linear comments** for additional context

## Team Communication

### Daily Process
1. Check **Linear** for assigned issues
2. **Pull latest develop** and rebase if working on feature
3. **Create feature branch** for new work
4. **Push updates** regularly with good commit messages
5. **Rebase daily** if working on long-running features
6. **Create PR** when feature complete
7. **Respond promptly** to code review feedback

### Best Practices
- **Ask questions early** - don't struggle alone for more than 30 minutes
- **Share knowledge** with team members in Slack/Discord
- **Test thoroughly** before creating PRs
- **Be responsive** to PR reviews (within 24 hours)
- **Help others** during code review - we all learn together
- **Communicate blockers** immediately - don't wait for standups

## Security & Best Practices

### Security Guidelines
- **Never commit** `.env` files, API keys, or secrets
- **Use environment variables** for all configuration
- **Validate all inputs** in API endpoints
- **Follow authentication patterns** established in codebase
- **Keep dependencies updated** regularly
- **Use HTTPS** in production environment variables
- **Sanitize user inputs** to prevent XSS/injection attacks

### Performance Guidelines  
- **Optimize images** before adding to public folder
- **Use React.memo** for expensive components
- **Implement proper loading states** for all async operations
- **Monitor bundle size** - keep under reasonable limits
- **Database queries** should use proper indexing
- **Use AWS S3** for file uploads, not local storage
- **Implement proper error boundaries** in React components

## Learning Resources

### Frontend
- [Next.js Documentation](https://nextjs.org/docs)
- [React JavaScript Guide](https://reactjs.org/docs/getting-started.html)
- [Modern JavaScript (ES6+)](https://javascript.info/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [AWS Cognito React Guide](https://docs.amplify.aws/lib/auth/getting-started/q/platform/js/)

### Backend
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Python Guide](https://supabase.com/docs/reference/python/introduction)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [AWS Cognito Python Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html)

### Git & Development
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Rebase Tutorial](https://git-scm.com/book/en/v2/Git-Branching-Rebasing)
- [Git Best Practices](https://git-scm.com/book/en/v2)
- [Linear Workflow](https://linear.app/docs)

## First-Time Setup Checklist

### Account Access
- [ ] Added to GitHub repositories (pulse-frontend, pulse-backend)
- [ ] Access to Linear workspace
- [ ] Team communication channels joined (Slack/Discord)
- [ ] AWS/Supabase credentials received from team lead

### Local Setup  
- [ ] Both repositories cloned and dependencies installed
- [ ] All Git branches set up locally (develop, staging, main)
- [ ] Environment variables configured for both frontend and backend
- [ ] Frontend running on localhost:3000
- [ ] Backend running on localhost:8000
- [ ] Can successfully make API calls between frontend/backend
- [ ] Authentication flow working locally

### Workflow Verification
- [ ] Understand branch strategy and naming conventions  
- [ ] Know how to rebase and when it's necessary
- [ ] Know how to link commits to Linear issues
- [ ] Created test feature branch successfully
- [ ] Made sample commit with proper format
- [ ] Successfully rebased test branch with develop
- [ ] Familiar with PR process and review guidelines

### First Contribution
- [ ] Pick up first Linear issue (start with small task)
- [ ] Create feature branch following naming convention
- [ ] Implement changes with proper commit messages  
- [ ] Rebase with latest develop before creating PR
- [ ] Create PR using template
- [ ] Address review feedback promptly
- [ ] Successfully merge to develop

---

## Welcome to the Team!

You're all set! If you have questions about this guide or run into any issues, don't hesitate to ask. We're excited to have you contributing to Pulse and building something great together.

Remember: **When in doubt, rebase!** It's better to rebase too often than to deal with messy merge conflicts later.

**Happy coding!**

---

*Last updated: December 2025 | For questions, contact @Huzaifa785*