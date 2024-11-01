import Navbar from '../../components/navigation/Navbar'
import WordList from './components/Wordlist'
// ... existing code ...

export default async function Component() {
  // 移除 useState 和 useEffect，改用服务器端数据获取

  const words = [
    {
      id: 1,
      word: "example",
      translation: "例子",
      example: "This is an example sentence." // 可选
    },
    // ...
  ]

  return (
    <>
      <Navbar />
      <div className="bg-slate-100 min-h-screen pt-20">
        <div className="container mx-auto p-4">
          <h1 className="text-2xl font-bold mb-6 text-black">词汇收藏(背单词功能待开发)</h1>
          
          {/* 使用客户端组件处理交互逻辑 */}
          <WordList initialWords={words} />
        </div>
      </div>
    </>
  )
}