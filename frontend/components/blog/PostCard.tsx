import Link from "next/link";
import type { PostMeta } from "@/app/blog/utils";

export default function PostCard({ post }: { post: PostMeta }) {
  return (
    <Link href={`/blog/${post.slug}`} className="group block border-b border-[#1e1e1e] py-6 hover:border-[#ef4444] transition-colors">
      <p className="font-mono text-[#444444] text-xs mb-2">{post.date}</p>
      <h2 className="font-serif text-[#f5f5f0] text-xl font-bold group-hover:text-[#ef4444] transition-colors mb-2">
        {post.title}
      </h2>
      <div className="flex gap-2">
        {post.tags.map((tag) => (
          <span key={tag} className="font-mono text-xs text-[#444444] border border-[#1e1e1e] px-2 py-0.5">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}
