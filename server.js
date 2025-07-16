// mcp-server.js
const express = require('express');
const { Octokit } = require('@octokit/rest');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// GitHub client setup
let octokit;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO_OWNER = process.env.REPO_OWNER || 'octocat';
const REPO_NAME = process.env.REPO_NAME || 'Hello-World';

if (GITHUB_TOKEN) {
    octokit = new Octokit({
        auth: GITHUB_TOKEN,
    });
} else {
    console.warn('GITHUB_TOKEN not set. Some features may not work.');
}

// MCP Tool definitions
const tools = {
    get_repository_info: {
        name: 'get_repository_info',
        description: 'Get basic repository information',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' }
            },
            required: ['owner', 'repo']
        }
    },
    list_issues: {
        name: 'list_issues',
        description: 'Get repository issues',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' },
                state: { type: 'string', enum: ['open', 'closed', 'all'] },
                per_page: { type: 'number', default: 30 }
            },
            required: ['owner', 'repo']
        }
    },
    get_file_contents: {
        name: 'get_file_contents',
        description: 'Read file contents from repository',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' },
                path: { type: 'string' },
                ref: { type: 'string', default: 'main' }
            },
            required: ['owner', 'repo', 'path']
        }
    },
    search_files: {
        name: 'search_files',
        description: 'Search for files by name or pattern',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' },
                query: { type: 'string' },
                path: { type: 'string', default: '' }
            },
            required: ['owner', 'repo', 'query']
        }
    },
    get_commits: {
        name: 'get_commits',
        description: 'Get recent commits',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' },
                sha: { type: 'string', default: 'main' },
                per_page: { type: 'number', default: 30 }
            },
            required: ['owner', 'repo']
        }
    },
    search_code: {
        name: 'search_code',
        description: 'Search for code content in repository',
        inputSchema: {
            type: 'object',
            properties: {
                owner: { type: 'string' },
                repo: { type: 'string' },
                query: { type: 'string' }
            },
            required: ['owner', 'repo', 'query']
        }
    }
};

// Helper function to handle GitHub API errors
const handleGitHubError = (error) => {
    if (error.status === 404) {
        return { error: 'Resource not found' };
    } else if (error.status === 403) {
        return { error: 'Rate limit exceeded or insufficient permissions' };
    } else {
        return { error: `GitHub API error: ${error.message}` };
    }
};

// Tool implementations
const toolImplementations = {
    async get_repository_info(args) {
        try {
            const { data } = await octokit.rest.repos.get({
                owner: args.owner,
                repo: args.repo
            });
            
            return {
                name: data.name,
                full_name: data.full_name,
                description: data.description,
                language: data.language,
                stars: data.stargazers_count,
                forks: data.forks_count,
                open_issues: data.open_issues_count,
                created_at: data.created_at,
                updated_at: data.updated_at,
                clone_url: data.clone_url,
                default_branch: data.default_branch
            };
        } catch (error) {
            return handleGitHubError(error);
        }
    },

    async list_issues(args) {
        try {
            const { data } = await octokit.rest.issues.listForRepo({
                owner: args.owner,
                repo: args.repo,
                state: args.state || 'open',
                per_page: args.per_page || 30
            });
            
            return data.map(issue => ({
                number: issue.number,
                title: issue.title,
                body: issue.body,
                state: issue.state,
                author: issue.user.login,
                created_at: issue.created_at,
                updated_at: issue.updated_at,
                labels: issue.labels.map(label => label.name),
                assignees: issue.assignees.map(assignee => assignee.login)
            }));
        } catch (error) {
            return handleGitHubError(error);
        }
    },

    async get_file_contents(args) {
        try {
            const { data } = await octokit.rest.repos.getContent({
                owner: args.owner,
                repo: args.repo,
                path: args.path,
                ref: args.ref || 'main'
            });
            
            if (data.type === 'file') {
                const content = Buffer.from(data.content, 'base64').toString('utf-8');
                return {
                    name: data.name,
                    path: data.path,
                    size: data.size,
                    content: content,
                    sha: data.sha
                };
            } else {
                return { error: 'Path is not a file' };
            }
        } catch (error) {
            return handleGitHubError(error);
        }
    },

    async search_files(args) {
        try {
            const query = `${args.query} repo:${args.owner}/${args.repo}`;
            const { data } = await octokit.rest.search.code({
                q: query,
                per_page: 30
            });
            
            return {
                total_count: data.total_count,
                items: data.items.map(item => ({
                    name: item.name,
                    path: item.path,
                    sha: item.sha,
                    url: item.html_url,
                    score: item.score
                }))
            };
        } catch (error) {
            return handleGitHubError(error);
        }
    },

    async get_commits(args) {
        try {
            const { data } = await octokit.rest.repos.listCommits({
                owner: args.owner,
                repo: args.repo,
                sha: args.sha || 'main',
                per_page: args.per_page || 30
            });
            
            return data.map(commit => ({
                sha: commit.sha,
                message: commit.commit.message,
                author: {
                    name: commit.commit.author.name,
                    email: commit.commit.author.email,
                    date: commit.commit.author.date
                },
                committer: {
                    name: commit.commit.committer.name,
                    email: commit.commit.committer.email,
                    date: commit.commit.committer.date
                },
                url: commit.html_url
            }));
        } catch (error) {
            return handleGitHubError(error);
        }
    },

    async search_code(args) {
        try {
            const query = `${args.query} repo:${args.owner}/${args.repo}`;
            const { data } = await octokit.rest.search.code({
                q: query,
                per_page: 30
            });
            
            return {
                total_count: data.total_count,
                items: data.items.map(item => ({
                    name: item.name,
                    path: item.path,
                    sha: item.sha,
                    url: item.html_url,
                    score: item.score,
                    text_matches: item.text_matches || []
                }))
            };
        } catch (error) {
            return handleGitHubError(error);
        }
    }
};

// Routes
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.get('/tools', (req, res) => {
    res.json(Object.values(tools));
});

app.post('/tools/:toolName', async (req, res) => {
    const { toolName } = req.params;
    const { arguments: args } = req.body;
    
    if (!toolImplementations[toolName]) {
        return res.status(404).json({ error: 'Tool not found' });
    }
    
    if (!octokit) {
        return res.status(500).json({ error: 'GitHub token not configured' });
    }
    
    try {
        const result = await toolImplementations[toolName](args);
        res.json(result);
    } catch (error) {
        console.error(`Error executing tool ${toolName}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`MCP Server running on port ${PORT}`);
    console.log(`GitHub token configured: ${!!GITHUB_TOKEN}`);
    console.log(`Default repository: ${REPO_OWNER}/${REPO_NAME}`);
});