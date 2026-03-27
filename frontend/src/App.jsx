import { useState, useRef, useEffect } from 'react'
import './index.css'

function App() {
  const [url, setUrl] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [ingested, setIngested] = useState(false)
  const [chunksProcessed, setChunksProcessed] = useState(0)

  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: 'Playlist processed! Ask me anything about the videos.' }
  ])
  const [chatting, setChatting] = useState(false)
  
  const endOfMessagesRef = useRef(null)

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  const handleIngest = async (e) => {
    e.preventDefault()
    if (!url) return
    
    setIngesting(true)
    try {
      const res = await fetch('http://localhost:8000/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      })
      const data = await res.json()
      if (res.ok) {
        setIngested(true)
        setChunksProcessed(data.chunks_processed)
      } else {
        alert("Error: " + data.detail)
      }
    } catch (err) {
      alert("Failed to connect to backend: " + err.message)
    } finally {
      setIngesting(false)
    }
  }

  const formatMessageWithCitations = (content) => {
    const regex = /\[([a-zA-Z0-9_-]{11}):([\d.]+)\]/g;
    const parts = [];
    let lastIndex = 0;
    
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      const videoId = match[1];
      const timeSecs = parseFloat(match[2]);
      const minutes = Math.floor(timeSecs / 60);
      const seconds = Math.floor(timeSecs % 60).toString().padStart(2, '0');
      
      parts.push(
        <a 
          key={match.index} 
          href={`https://youtube.com/watch?v=${videoId}&t=${Math.floor(timeSecs)}s`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center px-2 py-0.5 mx-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
        >
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 24 24"><path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/></svg>
          {minutes}:{seconds}
        </a>
      );
      lastIndex = match.index + match[0].length;
    }
    
    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }
    
    return parts.map((part, i) => {
      if (typeof part === 'string') {
        return part.split('\n').map((line, j) => (
          <span key={`${i}-${j}`}>
            {line}
            {j !== part.split('\n').length - 1 && <br />}
          </span>
        ))
      }
      return part
    })
  }

  const handleChat = async (e) => {
    e.preventDefault()
    if (!message) return

    const userMsg = message
    setMessage('')
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }])
    
    setChatting(true)
    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      })
      const data = await res.json()
      
      if (res.ok) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: data.answer }])
      } else {
        setChatHistory(prev => [...prev, { role: 'assistant', content: `Error: ${data.detail}` }])
      }
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: `Connection error: ${err.message}` }])
    } finally {
      setChatting(false)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-blue-500/30">
      <header className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold tracking-tight">YouTube RAG</h1>
        </div>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto p-6 flex flex-col gap-6">
        <section className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
          <h2 className="text-lg font-medium mb-2 text-white">1. Load Playlist</h2>
          <p className="text-sm text-neutral-400 mb-4">Ingest a YouTube playlist to chat with its contents.</p>
          
          <form onSubmit={handleIngest} className="flex gap-3">
            <input 
              type="url" 
              required
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/playlist?list=..." 
              className="flex-1 bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder-neutral-600"
            />
            <button 
              disabled={ingesting}
              className="px-6 py-2 bg-white text-black font-medium text-sm rounded-lg hover:bg-neutral-200 focus:ring-2 focus:ring-white/50 focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {ingesting ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Processing...
                </>
              ) : 'Ingest Data'}
            </button>
          </form>
          
          {ingested && (
            <div className="mt-4 px-4 py-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              Success! Extracted {chunksProcessed} chunks.
            </div>
          )}
        </section>

        <section className={`flex-1 flex flex-col bg-neutral-900/80 border border-neutral-800 rounded-2xl overflow-hidden shadow-xl backdrop-blur-md transition-all duration-500 ${!ingested ? 'opacity-50 pointer-events-none filter blur-sm' : ''}`}>
          <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900">
            <h2 className="text-lg font-medium text-white">2. Chat with Videos</h2>
            <p className="text-sm text-neutral-400">Ask complex questions. The AI will provide timestamped citations.</p>
          </div>
          
          <div className="flex-1 p-6 overflow-y-auto min-h-[400px] flex flex-col gap-4">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-br-sm' 
                    : 'bg-neutral-800 text-neutral-200 rounded-bl-sm border border-neutral-700/50 shadow-sm'
                }`}>
                  {msg.role === 'user' ? msg.content : formatMessageWithCitations(msg.content)}
                </div>
              </div>
            ))}
            {chatting && (
              <div className="flex justify-start">
                 <div className="bg-neutral-800 text-neutral-400 rounded-2xl rounded-bl-sm px-5 py-3 text-sm border border-neutral-700/50 flex items-center gap-1.5 shadow-sm">
                    <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce"></span>
                 </div>
              </div>
            )}
            <div ref={endOfMessagesRef} />
          </div>

          <form onSubmit={handleChat} className="p-4 border-t border-neutral-800 bg-neutral-900 focus-within:bg-neutral-800/80 transition-colors">
            <div className="relative">
              <input 
                type="text" 
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="Ask a question..." 
                disabled={chatting || !ingested}
                className="w-full bg-neutral-950 border border-neutral-700 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all disabled:opacity-50"
              />
              <button 
                disabled={chatting || !message.trim()}
                className="absolute right-1.5 top-1.5 bottom-1.5 aspect-square bg-blue-600 text-white rounded-lg flex items-center justify-center hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>
              </button>
            </div>
          </form>
        </section>
      </main>
    </div>
  )
}

export default App
