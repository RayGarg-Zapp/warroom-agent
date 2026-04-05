import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Bot, CheckSquare, ScrollText, Plug, ArrowRight, Lock, Eye, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  { icon: Bot, title: 'AI-Powered Detection', desc: 'Monitors Slack for incidents and classifies severity with reasoning.' },
  { icon: CheckSquare, title: 'Human-in-the-Loop', desc: 'Every high-risk action requires explicit human approval before execution.' },
  { icon: ScrollText, title: 'Full Audit Trail', desc: 'Every decision, approval, and action is logged and traceable.' },
  { icon: Lock, title: 'Security-First', desc: 'Scoped OAuth tokens, MFA step-up, encrypted credentials.' },
];

const tools = [
  { name: 'Slack', desc: 'Incident detection & DMs' },
  { name: 'Zoom', desc: 'War room creation' },
  { name: 'Google Calendar', desc: 'Bridge scheduling' },
  { name: 'Email', desc: 'Stakeholder notifications' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-2.5">
          <img src="/zappsec.png" alt="ZappSec" className="w-9 h-9 rounded-lg" />
          <span className="text-lg font-bold">WarRoom<span className="text-primary ml-1 font-semibold">Agent</span></span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/dashboard">
            <Button variant="outline" size="sm">Sign In</Button>
          </Link>
          <Link to="/dashboard">
            <Button size="sm" className="gap-1.5">Get Started <ArrowRight className="w-3.5 h-3.5" /></Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-8 pt-20 pb-16 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-ai-surface border border-ai-border text-xs font-semibold text-ai-accent mb-6">
            <Bot className="w-3.5 h-3.5" /> AI-Powered Incident Coordination
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold leading-tight mb-4 tracking-tight">
            Incident Response,<br />
            <span className="text-primary">Orchestrated by AI.</span><br />
            Controlled by You.
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            WarRoom Agent monitors your Slack channels, classifies incidents, identifies responders, and coordinates war rooms — with every action requiring your explicit approval.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link to="/dashboard">
              <Button size="lg" className="gap-2 px-6">
                Open Console <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link to="/integrations">
              <Button variant="outline" size="lg" className="gap-2 px-6">
                <Plug className="w-4 h-4" /> Connect Tools
              </Button>
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Trust highlights */}
      <section className="max-w-5xl mx-auto px-8 pb-16">
        <div className="flex items-center justify-center gap-8 mb-12">
          {[
            { icon: Eye, text: 'AI recommends' },
            { icon: CheckSquare, text: 'Human approves' },
            { icon: Zap, text: 'System executes' },
            { icon: ScrollText, text: 'Everything audited' },
          ].map((item, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.1 }}
              className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <item.icon className="w-4 h-4 text-primary" />
              {item.text}
              {i < 3 && <ArrowRight className="w-3 h-3 text-border ml-2" />}
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 + i * 0.1 }}
              className="glass-panel p-5">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
                <f.icon className="w-5 h-5 text-primary" />
              </div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Connected tools */}
      <section className="max-w-5xl mx-auto px-8 pb-20">
        <h2 className="text-xl font-bold text-center mb-8">Connected Tool Ecosystem</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {tools.map((t, i) => (
            <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 + i * 0.1 }}
              className="glass-panel p-4 text-center">
              <p className="font-semibold text-sm mb-1">{t.name}</p>
              <p className="text-xs text-muted-foreground">{t.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
