import type { GraphData } from "@/components/graph/types";

const DEV_GRAPH: GraphData = {
  nodes: [
    // Skills — languages
    { id: "skill-python",       type: "skill",      label: "Python",              description: "Primary language for backend and ML work.", metadata: { subtype: "language" } },
    { id: "skill-typescript",   type: "skill",      label: "TypeScript",          description: "Frontend and tooling.", metadata: { subtype: "language" } },
    { id: "skill-sql",          type: "skill",      label: "SQL",                 description: "Relational queries and data modeling.", metadata: { subtype: "language" } },
    { id: "skill-bash",         type: "skill",      label: "Bash",                description: "Scripting and CI/CD automation.", metadata: { subtype: "language" } },
    // Skills — frameworks
    { id: "skill-fastapi",      type: "skill",      label: "FastAPI",             description: "Async Python web framework for the backend API.", metadata: { subtype: "framework" } },
    { id: "skill-react",        type: "skill",      label: "React",               description: "Component-based UI with Next.js App Router.", metadata: { subtype: "framework" } },
    { id: "skill-nextjs",       type: "skill",      label: "Next.js",             description: "App Router, static export, server components.", metadata: { subtype: "framework" } },
    { id: "skill-tailwind",     type: "skill",      label: "Tailwind CSS",        description: "Utility-first styling.", metadata: { subtype: "framework" } },
    // Skills — infra
    { id: "skill-gcp",          type: "skill",      label: "Google Cloud",        description: "Cloud Run, GCS, Cloud CDN, IAM.", metadata: { subtype: "infra" } },
    { id: "skill-terraform",    type: "skill",      label: "Terraform",           description: "Infrastructure as code for GCP resources.", metadata: { subtype: "infra" } },
    { id: "skill-docker",       type: "skill",      label: "Docker",              description: "Containerisation for Cloud Run services.", metadata: { subtype: "infra" } },
    { id: "skill-github-actions", type: "skill",   label: "GitHub Actions",      description: "CI/CD pipelines for deploy and graph jobs.", metadata: { subtype: "infra" } },
    // Skills — ML/AI
    { id: "skill-llm",          type: "skill",      label: "LLMs",                description: "Prompt engineering, tool use, RAG.", metadata: { subtype: "ml" } },
    { id: "skill-rag",          type: "skill",      label: "RAG",                 description: "Retrieval-augmented generation pipelines.", metadata: { subtype: "ml" } },
    { id: "skill-embeddings",   type: "skill",      label: "Embeddings",          description: "Semantic search with vector similarity.", metadata: { subtype: "ml" } },
    { id: "skill-d3",           type: "skill",      label: "D3 / Force Graph",    description: "Force-directed graph layout and simulation.", metadata: { subtype: "framework" } },
    // Projects
    { id: "project-portfolio",  type: "project",    label: "tapshalkar.com",      description: "This portfolio — Next.js + FastAPI + knowledge graph.", metadata: {} },
    { id: "project-graphrag",   type: "project",    label: "Graph RAG Chat",      description: "Semantic search over a force-directed knowledge graph powering the chat agent.", metadata: {} },
    { id: "project-graph-gen",  type: "project",    label: "Graph Gen Job",       description: "Daily Cloud Run job that fetches APIs and synthesises graph.json via Claude.", metadata: {} },
    { id: "project-resume-parser", type: "project", label: "Resume Parser",       description: "Scheduled job that parses resume data into structured JSON.", metadata: {} },
    { id: "project-activity-feed", type: "project", label: "Activity Feed",       description: "Real-time feed of GitHub commits, Spotify, and Trakt data.", metadata: {} },
    // Experience
    { id: "experience-swe-1",   type: "experience", label: "Software Engineer",   description: "Full-stack and ML engineering in industry.", metadata: {} },
    { id: "experience-intern",  type: "experience", label: "Engineering Intern",  description: "Internship building data pipelines and internal tooling.", metadata: {} },
    // Education
    { id: "education-gt",       type: "education",  label: "Georgia Tech",        description: "B.S. Computer Science.", metadata: {} },
    // Interests
    { id: "interest-music",     type: "interest",   label: "Music",               description: "Avid listener across genres.", metadata: { subtype: "hobby" } },
    { id: "interest-books",     type: "interest",   label: "Books",               description: "Non-fiction, philosophy, and sci-fi.", metadata: { subtype: "hobby" } },
    { id: "interest-running",   type: "interest",   label: "Running",             description: "Regular long-distance runner.", metadata: { subtype: "hobby" } },
    { id: "interest-chess",     type: "interest",   label: "Chess",               description: "Casual player, following the competitive scene.", metadata: { subtype: "hobby" } },
    { id: "interest-film",      type: "interest",   label: "Film",                description: "Sci-fi and arthouse cinema.", metadata: { subtype: "hobby" } },
    { id: "interest-cooking",   type: "interest",   label: "Cooking",             description: "Experimenting with Indian and Mediterranean food.", metadata: { subtype: "hobby" } },
    // Health
    { id: "health-steps",       type: "health",     label: "Daily Steps",         description: "Tracking average daily step count.", metadata: {} },
    { id: "health-sleep",       type: "health",     label: "Sleep",               description: "Monitoring average nightly sleep duration.", metadata: {} },
    { id: "health-workouts",    type: "health",     label: "Workouts",            description: "Strength training and cardio sessions.", metadata: {} },
  ],
  edges: [
    // Frontend stack
    { source: "skill-typescript",   target: "skill-react",          type: "used_in",    weight: 1.5 },
    { source: "skill-react",        target: "skill-nextjs",         type: "used_in",    weight: 1.8 },
    { source: "skill-nextjs",       target: "project-portfolio",    type: "used_in",    weight: 2.0 },
    { source: "skill-tailwind",     target: "project-portfolio",    type: "used_in",    weight: 1.2 },
    { source: "skill-d3",           target: "project-portfolio",    type: "used_in",    weight: 1.5 },
    // Backend stack
    { source: "skill-python",       target: "skill-fastapi",        type: "used_in",    weight: 1.5 },
    { source: "skill-fastapi",      target: "project-portfolio",    type: "used_in",    weight: 1.8 },
    { source: "skill-fastapi",      target: "project-graphrag",     type: "used_in",    weight: 1.5 },
    // ML / AI
    { source: "skill-llm",          target: "skill-rag",            type: "relates_to", weight: 1.8 },
    { source: "skill-rag",          target: "skill-embeddings",     type: "relates_to", weight: 1.8 },
    { source: "skill-embeddings",   target: "project-graphrag",     type: "used_in",    weight: 2.0 },
    { source: "skill-llm",          target: "project-graph-gen",    type: "used_in",    weight: 2.0 },
    { source: "skill-python",       target: "project-graph-gen",    type: "used_in",    weight: 1.2 },
    // Infra
    { source: "skill-gcp",          target: "project-portfolio",    type: "used_in",    weight: 1.2 },
    { source: "skill-terraform",    target: "project-portfolio",    type: "used_in",    weight: 1.0 },
    { source: "skill-docker",       target: "project-portfolio",    type: "used_in",    weight: 1.0 },
    { source: "skill-github-actions", target: "project-portfolio",  type: "used_in",    weight: 1.0 },
    { source: "skill-gcp",          target: "project-graph-gen",    type: "used_in",    weight: 1.2 },
    // Project relations
    { source: "project-graphrag",   target: "project-portfolio",    type: "relates_to", weight: 1.5 },
    { source: "project-graph-gen",  target: "project-portfolio",    type: "relates_to", weight: 1.5 },
    { source: "project-activity-feed", target: "project-portfolio", type: "relates_to", weight: 1.2 },
    { source: "project-resume-parser", target: "project-portfolio", type: "relates_to", weight: 1.0 },
    { source: "skill-python",       target: "project-resume-parser", type: "used_in",   weight: 1.0 },
    { source: "skill-gcp",          target: "project-activity-feed", type: "used_in",   weight: 1.0 },
    // Experience
    { source: "experience-swe-1",   target: "skill-python",         type: "used_in",    weight: 1.5 },
    { source: "experience-swe-1",   target: "skill-sql",            type: "used_in",    weight: 1.2 },
    { source: "experience-swe-1",   target: "skill-gcp",            type: "used_in",    weight: 1.0 },
    { source: "experience-intern",  target: "skill-python",         type: "used_in",    weight: 1.0 },
    { source: "experience-intern",  target: "skill-sql",            type: "used_in",    weight: 0.8 },
    { source: "education-gt",       target: "experience-swe-1",     type: "relates_to", weight: 1.0 },
    { source: "education-gt",       target: "experience-intern",    type: "relates_to", weight: 1.0 },
    { source: "education-gt",       target: "skill-python",         type: "relates_to", weight: 0.8 },
    // Interests
    { source: "interest-running",   target: "health-steps",         type: "relates_to", weight: 1.5 },
    { source: "interest-running",   target: "health-workouts",      type: "relates_to", weight: 1.2 },
    { source: "health-sleep",       target: "health-workouts",      type: "relates_to", weight: 1.0 },
    { source: "interest-music",     target: "interest-running",     type: "relates_to", weight: 0.6 },
    { source: "interest-books",     target: "interest-film",        type: "relates_to", weight: 0.8 },
    { source: "interest-chess",     target: "interest-books",       type: "relates_to", weight: 0.5 },
    { source: "interest-cooking",   target: "interest-music",       type: "relates_to", weight: 0.4 },
  ],
};

export default DEV_GRAPH;
