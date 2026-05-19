import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import DocumentSelector from './DocumentSelector'

export default function ChatWindow({ availableDocs = [] }) {
  const { id: conversationId } = useParams()

  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [sending, setSending] = useState(false)
  const [input, setInput] = useState('')
  const [selectedDocs, setSelectedDocs] = useState(new Set())
  const [expandedSources, setExpandedSources] = useState(new Set())

  const messagesRef = useRef(null)
  const mountedRef = useRef(true)

  useEffect(() => () => { mountedRef.current = false }, [])

  // Scroll to bottom helper
  const scrollToBottom = useCallback(() => {
    if (!mountedRef.current) return
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }
  }, [])

  // Load conversation + initial messages on mount / conversationId change
  useEffect(() => {
    if (!conversationId) return

    setMessages([])
    setHasMore(false)
    setExpandedSources(new Set())
    setInput('')

    let cancelled = false

    async function load() {
      try {
        const [convRes, msgRes] = await Promise.all([
          api.get(`/conversations/${conversationId}`),
          api.get(`/conversations/${conversationId}/messages?size=50`),
        ])

        if (cancelled) return

        const conv = convRes.data
        setConversation(conv)

        if (conv.documentIds?.length) {
          setSelectedDocs(new Set(conv.documentIds))
        } else {
          setSelectedDocs(new Set())
        }

        const { content, hasMore: more } = msgRes.data
        setMessages([...(content || [])].reverse())
        setHasMore(!!more)
      } catch (err) {
        console.error('Failed to load conversation:', err)
      }
    }

    load().then(() => {
      // Give React time to render before scrolling
      setTimeout(scrollToBottom, 50)
    })

    return () => { cancelled = true }
  }, [conversationId, scrollToBottom])

  // Infinite scroll upward
  const handleScroll = useCallback(async () => {
    const el = messagesRef.current
    if (!el || !hasMore || loadingOlder) return
    if (el.scrollTop < 50) {
      const oldestId = messages[0]?.id
      if (!oldestId || oldestId === 'temp') return

      setLoadingOlder(true)
      const prevScrollHeight = el.scrollHeight
      try {
        const res = await api.get(
          `/conversations/${conversationId}/messages?before=${oldestId}&size=50`
        )
        const { content, hasMore: more } = res.data
        const older = [...(content || [])].reverse()
        setMessages(prev => [...older, ...prev])
        setHasMore(!!more)
        // Restore scroll position
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight - prevScrollHeight
        })
      } catch (err) {
        console.error('Failed to load older messages:', err)
      } finally {
        setLoadingOlder(false)
      }
    }
  }, [hasMore, loadingOlder, messages, conversationId])

  useEffect(() => {
    const el = messagesRef.current
    if (!el) return
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  // Send message
  async function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return

    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      role: 'USER',
      content: text,
      createdAt: new Date().toISOString(),
      sources: [],
    }

    setMessages(prev => [...prev, tempUserMsg])
    setSending(true)
    setInput('')

    try {
      const res = await api.post(`/conversations/${conversationId}/messages`, {
        message: text,
        documentIds: [...selectedDocs],
      })

      const assistantMsg = res.data
      setMessages(prev => [...prev, assistantMsg])
      setTimeout(scrollToBottom, 50)
    } catch (err) {
      console.error('Failed to send message:', err)
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        {
          id: 'err-' + Date.now(),
          role: 'ASSISTANT',
          content: 'Failed to send message. Please try again.',
          error: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  function toggleSources(msgId) {
    setExpandedSources(prev => {
      const next = new Set(prev)
      if (next.has(msgId)) next.delete(msgId)
      else next.add(msgId)
      return next
    })
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
  }

  // Empty state
  if (!conversationId) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        Select a conversation
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden h-full">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between bg-white flex-shrink-0">
        <h2 className="font-semibold text-gray-800 truncate">
          {conversation?.title || 'Conversation'}
        </h2>
        <DocumentSelector
          docs={availableDocs}
          selected={selectedDocs}
          onChange={setSelectedDocs}
        />
      </div>

      {/* Messages */}
      <div
        ref={messagesRef}
        className="flex-1 overflow-y-auto"
      >
        {loadingOlder && (
          <div className="text-center text-xs text-gray-400 py-2">Loading older messages…</div>
        )}

        {messages.length === 0 && !sending ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            No messages yet. Start the conversation!
          </div>
        ) : (
          <div className="flex flex-col gap-3 p-4">
            {messages.map(msg => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                sourcesExpanded={expandedSources.has(msg.id)}
                onToggleSources={() => toggleSources(msg.id)}
              />
            ))}

            {/* Thinking placeholder */}
            {sending && (
              <div className="self-start bg-gray-100 text-gray-800 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[70%]">
                <span className="italic text-gray-500">Thinking…</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t bg-white px-4 py-3 flex-shrink-0">
        <form onSubmit={handleSend} className="flex gap-2 items-end">
          <textarea
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
            placeholder="Type a message…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

function MessageBubble({ msg, sourcesExpanded, onToggleSources }) {
  const isUser = msg.role === 'USER'
  const hasSources = !isUser && msg.sources?.length > 0

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={
          isUser
            ? 'self-end bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[70%]'
            : msg.error
            ? 'self-start bg-red-100 text-red-700 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[70%]'
            : 'self-start bg-gray-100 text-gray-800 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[70%]'
        }
      >
        <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
      </div>

      {hasSources && (
        <div className="mt-1 max-w-[70%]">
          <button
            onClick={onToggleSources}
            className="text-xs text-blue-600 hover:underline"
          >
            Sources ({msg.sources.length}) {sourcesExpanded ? '▲' : '▼'}
          </button>

          {sourcesExpanded && (
            <div className="mt-1 border border-gray-200 rounded-lg bg-gray-50 p-2 space-y-1">
              {msg.sources.map((src, i) => (
                <div key={i} className="text-xs text-gray-600">
                  <span className="font-medium">{src.filename}</span>
                  {src.page != null && <span> p.{src.page}</span>}
                  {src.excerpt && (
                    <span className="text-gray-500"> — {src.excerpt}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
