import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bot, Send, Loader2, User, Copy, Check } from 'lucide-react';
import { chatWithAgent, type ChatMessage } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  incidentId: string;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1 rounded bg-muted/80 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
      title="Copy code"
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function renderMessageContent(content: string) {
  // Split by code fences and render code blocks with copy buttons
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, i) => {
    const codeMatch = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
    if (codeMatch) {
      const lang = codeMatch[1];
      const code = codeMatch[2].trimEnd();
      return (
        <div key={i} className="relative my-2 group">
          {lang && (
            <div className="text-[10px] text-muted-foreground bg-muted/60 px-3 py-1 rounded-t-md font-mono">
              {lang}
            </div>
          )}
          <pre className={cn(
            'bg-muted/40 p-3 rounded-md overflow-x-auto text-xs font-mono',
            lang && 'rounded-t-none'
          )}>
            <code>{code}</code>
          </pre>
          <CopyButton text={code} />
        </div>
      );
    }

    // Render markdown-lite: bold, inline code, checklist items, headers
    const lines = part.split('\n');
    return (
      <div key={i}>
        {lines.map((line, j) => {
          // Checklist items
          if (line.match(/^- \[ \] /)) {
            return (
              <div key={j} className="flex items-start gap-2 my-0.5">
                <input type="checkbox" disabled className="mt-1 rounded" />
                <span className="text-sm">{renderInline(line.replace(/^- \[ \] /, ''))}</span>
              </div>
            );
          }
          if (line.match(/^- \[x\] /i)) {
            return (
              <div key={j} className="flex items-start gap-2 my-0.5">
                <input type="checkbox" checked disabled className="mt-1 rounded" />
                <span className="text-sm line-through text-muted-foreground">
                  {renderInline(line.replace(/^- \[x\] /i, ''))}
                </span>
              </div>
            );
          }
          // Numbered list
          if (line.match(/^\d+\. /)) {
            return <p key={j} className="text-sm ml-2 my-0.5">{renderInline(line)}</p>;
          }
          // Bullet list
          if (line.match(/^[-*] /)) {
            return <p key={j} className="text-sm ml-2 my-0.5">{renderInline(line)}</p>;
          }
          // Headers
          if (line.match(/^###+ /)) {
            return <p key={j} className="text-sm font-bold mt-2 mb-1">{renderInline(line.replace(/^###+ /, ''))}</p>;
          }
          // Empty line
          if (!line.trim()) {
            return <div key={j} className="h-2" />;
          }
          return <p key={j} className="text-sm my-0.5">{renderInline(line)}</p>;
        })}
      </div>
    );
  });
}

function renderInline(text: string) {
  // Bold
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="bg-muted/60 px-1 py-0.5 rounded text-xs font-mono">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

const SUGGESTIONS = [
  'What is the root cause of this incident?',
  'Give me step-by-step remediation instructions',
  'What config changes are needed to fix this?',
  'What logs should I check first?',
];

export function IncidentChatWidget({ incidentId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (scrollRef.current) {
      const el = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (el) el.scrollTop = el.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    const newMessages: ChatMessage[] = [...messages, { role: 'user', content: msg }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const result = await chatWithAgent(incidentId, msg, messages);
      setMessages([...newMessages, { role: 'assistant', content: result.reply }]);
    } catch (err) {
      setMessages([
        ...newMessages,
        { role: 'assistant', content: `Error: ${err instanceof Error ? err.message : 'Failed to reach AI agent'}` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="glass-panel flex flex-col" style={{ height: '520px' }}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Bot className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-bold">AI Remediation Agent</h3>
          <p className="text-[11px] text-muted-foreground">Ask about fixes, configs, or next steps</p>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 px-4">
        {messages.length === 0 && !loading && (
          <div className="py-6 space-y-3">
            <p className="text-xs text-muted-foreground text-center mb-4">
              I have full context of this incident. Ask me anything about remediation.
            </p>
            <div className="grid grid-cols-1 gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left text-xs px-3 py-2 rounded-lg bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="py-3 space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn('flex gap-2', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-6 h-6 rounded-md bg-primary/10 flex-shrink-0 flex items-center justify-center mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  'max-w-[85%] rounded-lg px-3 py-2',
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted/50'
                )}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose-sm">{renderMessageContent(msg.content)}</div>
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-6 h-6 rounded-md bg-muted flex-shrink-0 flex items-center justify-center mt-0.5">
                  <User className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-2 items-start">
              <div className="w-6 h-6 rounded-md bg-primary/10 flex-shrink-0 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="bg-muted/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Thinking...
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about remediation, configs, next steps..."
            disabled={loading}
            className="flex-1 text-sm"
          />
          <Button
            size="icon"
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
