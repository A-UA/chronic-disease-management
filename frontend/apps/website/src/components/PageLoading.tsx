export default function PageLoading() {
  return (
    <div className="space-y-6 p-2 animate-fade-in">
      {/* 标题骨架 */}
      <div className="h-8 w-48 rounded-lg animate-shimmer" />

      {/* 卡片骨架 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 rounded-xl animate-shimmer"
            style={{ animationDelay: `${i * 0.1}s` }}
          />
        ))}
      </div>

      {/* 内容骨架 */}
      <div className="h-64 rounded-xl animate-shimmer" style={{ animationDelay: "0.4s" }} />
    </div>
  );
}
