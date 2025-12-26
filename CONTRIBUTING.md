# Contributing to Pulse

Thanks for your interest in contributing to Pulse! This guide will help you get up and running with our development workflow.

## Getting Started

### Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.9+ and pip  
- **Git** configured with your GitHub account
- Access to team **Linear** workspace
- **Supabase** credentials (provided by team lead)

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
python -m venv pulse-env
source pulse-env/bin/activate  # Windows: pulse-env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Verify setup:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

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
 routers/     # FastAPI route handlers
 services/    # Business logic
 config/      # Configuration & database
 models/      # Data models
```

## Branch Strategy & Workflow

### Branch Structure
```
main (Production)  staging (Pre-prod)  develop (Integration)  feature/PULSE-XXX
```

### Branch Types & Naming
```bash
feature/PULSE-123-user-authentication    # New features
bugfix/PULSE-124-login-error            # Bug fixes  
hotfix/PULSE-125-critical-security-fix  # Production hotfixes
```

### Daily Workflow

1. **Start new work:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/PULSE-XXX-descriptive-name
```

2. **Regular commits:**
```bash
git add .
git commit -m "feat: add user authentication (PULSE-123)"
git push origin feature/PULSE-XXX-descriptive-name
```

3. **Keep updated:**
```bash
git checkout develop && git pull origin develop
git checkout feature/PULSE-XXX-descriptive-name  
git rebase develop
```

4. **Create Pull Request:**
   - Base: `develop`
   - Include Linear issue number in title
   - Use PR template
   - Request review from team member

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
```

**Required format:** `type(scope): description (PULSE-XXX)`

## Linear Integration

### Issue Workflow
```
Open  In Progress  In Review  Testing  Done
```

### Linking Work
- **Branch names:** Must include Linear issue number
- **Commit messages:** Include `(PULSE-XXX)` at the end
- **PR titles:** Include Linear issue number
- **PR description:** Use `Closes PULSE-XXX`

Example:
```bash
git checkout -b feature/PULSE-123-user-dashboard
git commit -m "feat: implement user dashboard layout (PULSE-123)"
```

## Environment Setup

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Backend (.env)
```env
# Database (get from team lead)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Application
DEBUG=true
APP_NAME="Pulse Backend API"
API_V1_STR="/api/v1"
```

** Never commit .env files - they're in .gitignore for security**

## Code Standards

### Frontend
- **JavaScript** for all components and logic
- **ESLint + Prettier** - run `npm run lint` before committing
- **Tailwind CSS** for styling - avoid custom CSS
- **Component naming:** PascalCase (e.g., `UserDashboard.js`)
- **File structure:** Use `.js` for components, `.json` for config

### Backend  
- **PEP 8** Python style guide
- **Type hints** for all function parameters/returns
- **Docstrings** for all public functions/classes
- **FastAPI** conventions - async/await for database operations

### Pre-commit Checklist
- [ ] Code follows style guidelines
- [ ] All tests pass locally (`npm test` / `pytest`)
- [ ] No console errors in browser
- [ ] Linear issue linked in commit
- [ ] Environment variables updated if needed

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

## Screenshots
(if applicable)
```

### Review Process
1. **Automated checks** must pass (GitHub Actions)
2. **At least 1 approval** from team member required
3. **Test in preview environment** (auto-deployed)
4. **Squash and merge** for clean commit history

### For Reviewers
- Test the feature in preview environment  
- Check code style and conventions
- Verify Linear issue is properly linked
- Look for security/performance issues
- Be constructive in feedback

## Deployment

### Automatic Deployments
| Environment | Trigger | URL |
|-------------|---------|-----|
| **Production** | `main` branch | https://pulse-so.vercel.app |
| **Staging** | `staging` branch | *-git-staging-*.vercel.app |
| **Development** | `develop` branch | *-git-develop-*.vercel.app |
| **Preview** | Any PR | *-git-branch-*.vercel.app |

### Environment Flow
```
feature/PULSE-XXX  develop  staging  main
                                      
    Preview         Dev     Staging  Production
```

**All deployments are automatic via Vercel when you push/merge.**

## Troubleshooting

### Common Issues

**"Cannot connect to backend"**
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify environment variables
cat .env.local | grep NEXT_PUBLIC_API_URL

# Restart services
npm run dev        # Frontend
uvicorn app.main:app --reload  # Backend
```

**"Module not found" errors**
```bash
# Frontend
rm -rf node_modules package-lock.json
npm install

# Backend
pip install -r requirements.txt
```

**CORS errors in browser**
1. Check `app/main.py` CORS configuration
2. Verify your local URL is in `allow_origins`
3. Clear browser cache

**"Not authenticated" API errors**
1. Check if logged in to application
2. Clear browser local storage
3. Re-login to get fresh tokens

### Getting Help

1. **Check this guide** first
2. **Search existing GitHub issues** 
3. **Ask in team chat** for quick questions
4. **Create new issue** for bugs/feature requests
5. **Tag @Huzaifa785** for urgent blockers

## Quick Reference

### Essential Commands
```bash
# Start new feature  
git checkout develop && git pull origin develop
git checkout -b feature/PULSE-XXX-description

# Daily workflow
git add .
git commit -m "feat: description (PULSE-XXX)"  
git push origin feature/PULSE-XXX-description

# Keep branch updated
git checkout develop && git pull origin develop
git checkout feature/PULSE-XXX-description
git rebase develop

# Local development
npm run dev                      # Frontend
uvicorn app.main:app --reload   # Backend
npm run lint                    # Check code style  
npm test                        # Run tests
```

### Important URLs
- **Frontend Repo:** https://github.com/HealthEase-Technologies/pulse-frontend
- **Backend Repo:** https://github.com/HealthEase-Technologies/pulse-backend  
- **Production:** https://pulse-so.vercel.app
- **API Docs:** https://pulse-backend-so.vercel.app/docs
- **Staging Frontend:** https://pulse-frontend-git-staging-healthease-technologies.vercel.app

## Team Communication

### Daily Process
1. Check **Linear** for assigned issues
2. **Pull latest** from develop branch
3. **Create feature branch** for new work
4. **Push updates** regularly with good commit messages
5. **Create PR** when feature complete
6. **Respond promptly** to code review feedback

### Best Practices
- **Ask questions early** - don't struggle alone
- **Share knowledge** with team members  
- **Test thoroughly** before creating PRs
- **Be responsive** to PR reviews
- **Help others** during code review

## Security & Best Practices

### Security Guidelines
- **Never commit** `.env` files or secrets
- **Use environment variables** for all configuration
- **Validate all inputs** in API endpoints
- **Follow authentication patterns** established in codebase
- **Keep dependencies updated** regularly

### Performance Guidelines  
- **Optimize images** before adding to public folder
- **Use React.memo** for expensive components
- **Implement proper loading states**
- **Monitor bundle size** - keep under reasonable limits
- **Database queries** should use proper indexing

## Learning Resources

### Frontend
- [Next.js Documentation](https://nextjs.org/docs)
- [React JavaScript Guide](https://reactjs.org/docs/getting-started.html)
- [Modern JavaScript (ES6+)](https://javascript.info/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)

### Backend
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Python Guide](https://supabase.com/docs/reference/python/introduction)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### Tools
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2)
- [Linear Workflow](https://linear.app/docs)

## First-Time Setup Checklist

### Account Access
- [ ] Added to GitHub repositories (pulse-frontend, pulse-backend)
- [ ] Access to Linear workspace
- [ ] Team communication channels joined
- [ ] Supabase credentials received

### Local Setup  
- [ ] Both repositories cloned and dependencies installed
- [ ] Environment variables configured
- [ ] Frontend running on localhost:3000
- [ ] Backend running on localhost:8000
- [ ] Can successfully make API calls between frontend/backend

### Workflow Verification
- [ ] Understand branch strategy and naming conventions  
- [ ] Know how to link commits to Linear issues
- [ ] Created test feature branch
- [ ] Made sample commit with proper format
- [ ] Familiar with PR process and review guidelines

### First Contribution
- [ ] Pick up first Linear issue
- [ ] Create feature branch following naming convention
- [ ] Implement changes with proper commit messages  
- [ ] Create PR using template
- [ ] Address review feedback  
- [ ] Successfully merge to develop

---

## Welcome to the Team!

You're all set! If you have questions about this guide or run into any issues, don't hesitate to ask. We're excited to have you contributing to Pulse and building something great together.

**Happy coding!**

---

*Last updated: December 2025 | For questions, contact @Huzaifa785*