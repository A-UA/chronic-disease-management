import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import './index.css'

// 基础 App 组件，稍后会在 Task 4 中完善布局
const App = () => (
  <div className="flex items-center justify-center h-screen bg-gray-50">
    <h1 className="text-2xl font-bold text-blue-600">慢病管理系统后台已就绪</h1>
  </div>
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
