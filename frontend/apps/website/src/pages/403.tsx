import { useNavigate } from "react-router-dom";

export default function Forbidden() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
      <div className="text-8xl font-bold text-primary/10 mb-4">403</div>
      <h1 className="text-2xl font-bold text-foreground mb-2">无权限访问</h1>
      <p className="text-muted-foreground mb-8">抱歉，您没有权限访问此页面</p>
      <button
        type="button"
        onClick={() => void navigate("/")}
        className="px-6 py-2.5 rounded-lg gradient-primary text-white font-medium text-sm border-0 cursor-pointer hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-md"
      >
        返回首页
      </button>
    </div>
  );
}
