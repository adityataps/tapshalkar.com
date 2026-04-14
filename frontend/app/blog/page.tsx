import { getAllPosts } from "./utils";
import PostCard from "@/components/blog/PostCard";

export default function BlogIndex() {
  const posts = getAllPosts();

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="font-mono text-[#ef4444] text-xs tracking-widest uppercase mb-12">~/writing</p>
      {posts.length === 0 ? (
        <p className="text-[#777777] text-sm">No posts yet.</p>
      ) : (
        posts.map((post) => <PostCard key={post.slug} post={post} />)
      )}
    </div>
  );
}
