import { getAllPosts, getPost } from "../utils";
import { MDXRemote } from "next-mdx-remote/rsc";

export async function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getPost(slug);
  const wordsPerMinute = 200;
  const wordCount = post.content.split(/\s+/).length;
  const readTime = Math.max(1, Math.round(wordCount / wordsPerMinute));

  return (
    <article className="mx-auto max-w-2xl px-6 py-16">
      <p className="font-mono text-[#444444] text-xs mb-2">{post.date} · {readTime} min read</p>
      <h1 className="font-serif text-4xl font-bold text-[#f5f5f0] mb-4">{post.title}</h1>
      <div className="flex gap-2 mb-10">
        {post.tags.map((tag) => (
          <span key={tag} className="font-mono text-xs text-[#444444] border border-[#1e1e1e] px-2 py-0.5">
            {tag}
          </span>
        ))}
      </div>
      <div className="prose prose-invert prose-sm max-w-none
        prose-headings:font-serif prose-headings:text-[#f5f5f0]
        prose-p:text-[#444444] prose-p:leading-relaxed
        prose-a:text-[#ef4444] prose-a:no-underline hover:prose-a:underline
        prose-code:text-[#ef4444] prose-code:font-mono prose-code:text-xs
        prose-pre:bg-[#111111] prose-pre:border prose-pre:border-[#1e1e1e]">
        <MDXRemote source={post.content} />
      </div>
    </article>
  );
}
