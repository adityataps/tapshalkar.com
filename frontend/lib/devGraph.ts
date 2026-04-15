import type { GraphData } from "@/components/graph/types";

const DEV_GRAPH: GraphData = {
  nodes: [
    { id: "skill-python",    type: "skill",      label: "Python",          description: "Primary language for backend and ML work.", metadata: { subtype: "language" } },
    { id: "skill-typescript",type: "skill",      label: "TypeScript",      description: "Frontend and tooling.", metadata: { subtype: "language" } },
    { id: "skill-llm",       type: "skill",      label: "LLMs",            description: "Prompt engineering, tool use, RAG.", metadata: { subtype: "ml" } },
    { id: "project-portfolio",type: "project",   label: "tapshalkar.com",  description: "This portfolio — Next.js + FastAPI + knowledge graph.", metadata: {} },
    { id: "project-graphrag", type: "project",   label: "Graph RAG",       description: "Semantic search over a force-directed knowledge graph.", metadata: {} },
    { id: "interest-music",   type: "interest",  label: "Music",           description: "Avid listener across genres.", metadata: { subtype: "hobby" } },
    { id: "experience-swe",   type: "experience",label: "Software Engineer",description: "Industry experience building production systems.", metadata: {} },
  ],
  edges: [
    { source: "skill-python",     target: "project-portfolio",  type: "used_in",   weight: 1.5 },
    { source: "skill-typescript", target: "project-portfolio",  type: "used_in",   weight: 1.5 },
    { source: "skill-llm",        target: "project-graphrag",   type: "used_in",   weight: 2.0 },
    { source: "skill-python",     target: "project-graphrag",   type: "used_in",   weight: 1.2 },
    { source: "project-graphrag", target: "project-portfolio",  type: "relates_to", weight: 1.0 },
    { source: "experience-swe",   target: "skill-python",       type: "used_in",   weight: 1.0 },
    { source: "interest-music",   target: "experience-swe",     type: "relates_to", weight: 0.5 },
  ],
};

export default DEV_GRAPH;
