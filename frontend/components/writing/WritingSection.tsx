import Link from "next/link";
import { getAllPosts } from "@/app/blog/utils";

export default function WritingSection() {
  const posts = getAllPosts();

  return (
    <section id="writing" className="px-8 md:px-16 py-16 border-t border-[#1a1a1a]">
      <h2 className="font-serif text-2xl text-[#f5f5f0] mb-8">Writing</h2>
      {posts.length === 0 ? (
        <p className="text-[#444444] text-sm">No posts yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group flex flex-col gap-2 p-5 border border-[#1a1a1a] hover:border-[#444444] transition-colors"
            >
              <span className="text-[#444444] text-xs">{post.date}</span>
              <h3 className="font-serif text-[#f5f5f0] group-hover:text-[#ef4444] transition-colors">
                {post.title}
              </h3>
              {post.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-auto pt-3">
                  {post.tags.map((tag) => (
                    <span key={tag} className="text-[#444444] text-xs">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
