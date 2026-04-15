import type { GraphData } from "@/components/graph/types";

const DEV_GRAPH: GraphData = {
  nodes: [
    // Skills
    { id: "skill-python",      type: "skill",      label: "Python",            description: "Primary language for backend and ML work.", metadata: { subtype: "language" } },
    { id: "skill-typescript",  type: "skill",      label: "TypeScript",        description: "Frontend and tooling.", metadata: { subtype: "language" } },
    { id: "skill-llm",         type: "skill",      label: "LLMs",              description: "Prompt engineering, tool use, RAG.", metadata: { subtype: "ml" } },
    { id: "skill-gcp",         type: "skill",      label: "Google Cloud",      description: "Cloud Run, GCS, Cloud CDN, IAM.", metadata: { subtype: "infra" } },
    { id: "skill-terraform",   type: "skill",      label: "Terraform",         description: "Infrastructure as code for GCP resources.", metadata: { subtype: "infra" } },
    { id: "skill-react",       type: "skill",      label: "React",             description: "Component-based UI with Next.js App Router.", metadata: { subtype: "framework" } },
    { id: "skill-fastapi",     type: "skill",      label: "FastAPI",           description: "Async Python web framework for the backend API.", metadata: { subtype: "framework" } },
    // Projects
    { id: "project-portfolio", type: "project",    label: "tapshalkar.com",    description: "This portfolio — Next.js + FastAPI + knowledge graph.", metadata: {} },
    { id: "project-graphrag",  type: "project",    label: "Graph RAG",         description: "Semantic search over a force-directed knowledge graph.", metadata: {} },
    { id: "project-graph-gen", type: "project",    label: "Graph Gen Job",     description: "Daily Cloud Run job that fetches APIs and builds graph.json via Claude.", metadata: {} },
    // Experience
    { id: "experience-swe",    type: "experience", label: "Software Engineer", description: "Industry experience building production systems.", metadata: {} },
    // Education
    { id: "education-gt",      type: "education",  label: "Georgia Tech",      description: "B.S. Computer Science.", metadata: {} },
    // Interests
    { id: "interest-music",    type: "interest",   label: "Music",             description: "Avid listener across genres.", metadata: { subtype: "hobby" } },
    { id: "interest-books",    type: "interest",   label: "Books",             description: "Non-fiction, philosophy, and sci-fi.", metadata: { subtype: "hobby" } },
    { id: "interest-running",  type: "interest",   label: "Running",           description: "Regular long-distance runner.", metadata: { subtype: "hobby" } },
  ],
  edges: [
    { source: "skill-python",      target: "project-portfolio",  type: "used_in",    weight: 1.5 },
    { source: "skill-typescript",  target: "project-portfolio",  type: "used_in",    weight: 1.5 },
    { source: "skill-react",       target: "project-portfolio",  type: "used_in",    weight: 1.5 },
    { source: "skill-fastapi",     target: "project-portfolio",  type: "used_in",    weight: 1.2 },
    { source: "skill-gcp",         target: "project-portfolio",  type: "used_in",    weight: 1.2 },
    { source: "skill-terraform",   target: "project-portfolio",  type: "used_in",    weight: 1.0 },
    { source: "skill-llm",         target: "project-graphrag",   type: "used_in",    weight: 2.0 },
    { source: "skill-python",      target: "project-graphrag",   type: "used_in",    weight: 1.2 },
    { source: "skill-llm",         target: "project-graph-gen",  type: "used_in",    weight: 1.8 },
    { source: "skill-python",      target: "project-graph-gen",  type: "used_in",    weight: 1.2 },
    { source: "skill-gcp",         target: "project-graph-gen",  type: "used_in",    weight: 1.0 },
    { source: "project-graphrag",  target: "project-portfolio",  type: "relates_to", weight: 1.0 },
    { source: "project-graph-gen", target: "project-portfolio",  type: "relates_to", weight: 1.0 },
    { source: "experience-swe",    target: "skill-python",       type: "used_in",    weight: 1.0 },
    { source: "experience-swe",    target: "skill-gcp",          type: "used_in",    weight: 0.8 },
    { source: "education-gt",      target: "experience-swe",     type: "relates_to", weight: 1.0 },
    { source: "education-gt",      target: "skill-python",       type: "relates_to", weight: 0.8 },
    { source: "interest-music",    target: "interest-running",   type: "relates_to", weight: 0.5 },
    { source: "interest-books",    target: "interest-music",     type: "relates_to", weight: 0.4 },
  ],
};

export default DEV_GRAPH;
