"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const router = useRouter();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (owner.trim() && repo.trim()) {
      router.push(`/repo/${owner.trim()}/${repo.trim()}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8"
      style={{ background: "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)" }}>
      <div className="relative mb-12">
        <div className="absolute -inset-1 rounded-2xl opacity-50 blur-xl"
          style={{ background: "linear-gradient(135deg, #6c63ff, #00ff88)" }} />
        <h1 className="relative text-5xl font-bold tracking-tight"
          style={{ color: "#e0e0ff" }}>
          GitHub <span style={{ color: "#6c63ff" }}>Intelligence</span>
        </h1>
      </div>
      <p className="text-lg mb-10 max-w-md text-center" style={{ color: "#8888aa" }}>
        Repository health analysis, risk detection, and autonomous investigation
      </p>

      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-5">
        <div>
          <label htmlFor="owner" className="block text-sm font-medium mb-2" style={{ color: "#8888aa" }}>
            Owner
          </label>
          <input
            id="owner"
            type="text"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="e.g. facebook"
            className="w-full px-4 py-3 rounded-lg transition-all duration-200"
            required
          />
        </div>
        <div>
          <label htmlFor="repo" className="block text-sm font-medium mb-2" style={{ color: "#8888aa" }}>
            Repository
          </label>
          <input
            id="repo"
            type="text"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="e.g. react"
            className="w-full px-4 py-3 rounded-lg transition-all duration-200"
            required
          />
        </div>
        <button
          type="submit"
          className="w-full py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
          style={{
            background: "linear-gradient(135deg, #6c63ff, #5a52d5)",
            boxShadow: "0 4px 20px rgba(108, 99, 255, 0.3)",
          }}
        >
          Investigate
        </button>
      </form>
    </div>
  );
}
