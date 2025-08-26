import Link from 'next/link';

export default function Home() {
  return (
    <div className="font-sans min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center p-6 bg-black/20 backdrop-blur-sm sticky top-0 z-50">
        <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          WaddleBot
        </div>
        <div className="hidden md:flex gap-8">
          <Link href="/features" className="hover:text-blue-300 transition-colors">Features</Link>
          <Link href="/pricing" className="hover:text-blue-300 transition-colors">Pricing</Link>
          <Link href="/solutions" className="hover:text-blue-300 transition-colors">Solutions</Link>
          <a href="https://docs.waddlebot.io" className="hover:text-blue-300 transition-colors">Documentation</a>
          <Link href="/contact" className="hover:text-blue-300 transition-colors">Contact</Link>
        </div>
        <div className="flex gap-4">
          <Link href="/demo" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-semibold">
            Live Demo
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20 text-center">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
            <span className="px-4 py-2 bg-green-500/20 text-green-300 rounded-full text-sm font-semibold">
              🆓 Open Source & Self-Hosted • Deploy Anywhere • Zero Cost
            </span>
          </div>
          <h1 className="text-6xl md:text-8xl font-bold mb-8 bg-gradient-to-r from-blue-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent leading-tight">
            The Future of Community Management
          </h1>
          <p className="text-2xl md:text-3xl mb-8 text-gray-200 max-w-4xl mx-auto leading-relaxed">
            Open source community management platform with enterprise-grade automation, AI-powered interactions, and real-time analytics
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center items-center mb-12">
            <a
              href="https://github.com/WaddleBot/WaddleBot"
              className="px-10 py-5 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 rounded-xl text-xl font-semibold transition-all transform hover:scale-105 shadow-lg"
            >
              Get Open Source
            </a>
            <Link
              href="/demo"
              className="px-10 py-5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-xl text-xl font-semibold transition-all transform hover:scale-105 shadow-lg"
            >
              Try Cloud Hosted
            </Link>
            <Link
              href="/pricing"
              className="px-10 py-5 border-2 border-white/30 hover:bg-white/10 rounded-xl text-xl font-semibold transition-colors"
            >
              See Pricing
            </Link>
          </div>
          
          {/* Trust Indicators */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto text-center">
            <div>
              <div className="text-3xl font-bold text-blue-400">1000+</div>
              <div className="text-gray-400 text-sm">Communities</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-400">99.9%</div>
              <div className="text-gray-400 text-sm">Uptime</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-indigo-400">50M+</div>
              <div className="text-gray-400 text-sm">Messages Processed</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400">24/7</div>
              <div className="text-gray-400 text-sm">Support</div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Statement */}
      <section className="bg-black/20 backdrop-blur-sm py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-bold mb-8">
              Community Management is <span className="text-red-400">Broken</span>
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-xl">
                <div className="text-red-400 text-4xl mb-4">😤</div>
                <h3 className="text-xl font-bold mb-3 text-red-400">Manual Everything</h3>
                <p className="text-gray-300">Moderators spending hours on repetitive tasks instead of building community</p>
              </div>
              <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-xl">
                <div className="text-red-400 text-4xl mb-4">💸</div>
                <h3 className="text-xl font-bold mb-3 text-red-400">Platform Lock-in</h3>
                <p className="text-gray-300">Separate tools for Discord, Twitch, and Slack with no unified management</p>
              </div>
              <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-xl">
                <div className="text-red-400 text-4xl mb-4">📊</div>
                <h3 className="text-xl font-bold mb-3 text-red-400">No Insights</h3>
                <p className="text-gray-300">Flying blind without analytics, engagement metrics, or growth insights</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Solution */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold mb-6">
                Meet <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">WaddleBot</span>
              </h2>
              <p className="text-xl text-gray-300 max-w-3xl mx-auto">
                Open source, self-hosted community management platform with enterprise-grade reliability and unlimited customization
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <h3 className="text-3xl font-bold mb-6 text-blue-300">Unified Control Center</h3>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-green-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <h4 className="font-semibold mb-1">One Dashboard, All Platforms</h4>
                      <p className="text-gray-400">Manage Discord servers, Twitch channels, and Slack workspaces from a single interface</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-green-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <h4 className="font-semibold mb-1">AI-Powered Automation</h4>
                      <p className="text-gray-400">Smart moderation, automated responses, and intelligent content curation</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="w-6 h-6 rounded-full bg-green-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <h4 className="font-semibold mb-1">Real-time Analytics</h4>
                      <p className="text-gray-400">Deep insights into engagement, growth trends, and community health</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 p-8 rounded-2xl border border-white/10">
                <div className="bg-black/30 p-4 rounded-lg mb-4">
                  <div className="text-green-400 text-sm font-mono">$ waddlebot status</div>
                  <div className="text-white text-sm font-mono mt-2">
                    ✅ Discord: 5 servers, 12k members<br/>
                    ✅ Twitch: 3 channels, 850 followers<br/>
                    ✅ Slack: 2 workspaces, 200 users<br/>
                    🤖 AI responses: 1,247 today<br/>
                    📊 Engagement up 34% this week
                  </div>
                </div>
                <p className="text-gray-300 text-sm">Live dashboard showing your community health across all platforms</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section className="bg-black/10 backdrop-blur-sm py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-16">
              Everything You Need to Scale
            </h2>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-blue-500/50 transition-colors">
                <div className="text-4xl mb-4">🤖</div>
                <h3 className="text-xl font-bold mb-4 text-blue-300">AI Assistant</h3>
                <p className="text-gray-300 mb-4">Intelligent chat responses, content moderation, and community insights powered by Ollama and OpenAI</p>
                <div className="text-sm text-blue-400">→ Reduce moderation time by 80%</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-purple-500/50 transition-colors">
                <div className="text-4xl mb-4">🎵</div>
                <h3 className="text-xl font-bold mb-4 text-purple-300">Music Integration</h3>
                <p className="text-gray-300 mb-4">Spotify and YouTube Music controls with OBS browser source overlays for streamers</p>
                <div className="text-sm text-purple-400">→ Enhance stream production value</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-indigo-500/50 transition-colors">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="text-xl font-bold mb-4 text-indigo-300">Analytics & Insights</h3>
                <p className="text-gray-300 mb-4">Real-time community metrics, engagement tracking, and growth analytics across all platforms</p>
                <div className="text-sm text-indigo-400">→ Make data-driven decisions</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-green-500/50 transition-colors">
                <div className="text-4xl mb-4">⚡</div>
                <h3 className="text-xl font-bold mb-4 text-green-300">Custom Commands</h3>
                <p className="text-gray-300 mb-4">Unlimited custom commands, aliases, and automated workflows tailored to your community</p>
                <div className="text-sm text-green-400">→ Automate repetitive tasks</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-yellow-500/50 transition-colors">
                <div className="text-4xl mb-4">🛡️</div>
                <h3 className="text-xl font-bold mb-4 text-yellow-300">Advanced Moderation</h3>
                <p className="text-gray-300 mb-4">Smart spam detection, automated warnings, and coordinated moderation across platforms</p>
                <div className="text-sm text-yellow-400">→ Keep communities safe 24/7</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/10 hover:border-pink-500/50 transition-colors">
                <div className="text-4xl mb-4">🚀</div>
                <h3 className="text-xl font-bold mb-4 text-pink-300">Enterprise Scale</h3>
                <p className="text-gray-300 mb-4">Kubernetes deployment, high availability, and dedicated support for large communities</p>
                <div className="text-sm text-pink-400">→ Handle millions of messages</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-16">
              Trusted by Leading Communities
            </h2>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white/5 p-8 rounded-xl border border-white/10">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-xl font-bold">
                    G
                  </div>
                  <div>
                    <div className="font-semibold">GameDev Central</div>
                    <div className="text-gray-400 text-sm">50K+ members</div>
                  </div>
                </div>
                <p className="text-gray-300 mb-4">
                  &ldquo;WaddleBot transformed our community management. We went from spending 20 hours a week on moderation to just 3 hours, while our engagement increased 45%.&rdquo;
                </p>
                <div className="text-sm text-blue-400">- Sarah Chen, Community Manager</div>
              </div>
              
              <div className="bg-white/5 p-8 rounded-xl border border-white/10">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-xl font-bold">
                    S
                  </div>
                  <div>
                    <div className="font-semibold">StreamerHub</div>
                    <div className="text-gray-400 text-sm">25K+ followers</div>
                  </div>
                </div>
                <p className="text-gray-300 mb-4">
                  &ldquo;The music integration and OBS browser sources are game-changers. Our stream production quality went up dramatically and chat engagement doubled.&rdquo;
                </p>
                <div className="text-sm text-purple-400">- Mike Rodriguez, Twitch Streamer</div>
              </div>
              
              <div className="bg-white/5 p-8 rounded-xl border border-white/10">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-green-500 to-blue-500 flex items-center justify-center text-xl font-bold">
                    T
                  </div>
                  <div>
                    <div className="font-semibold">TechStartup Co.</div>
                    <div className="text-gray-400 text-sm">500+ employees</div>
                  </div>
                </div>
                <p className="text-gray-300 mb-4">
                  &ldquo;Having unified Slack and Discord management was exactly what we needed. The AI assistant handles 80% of common questions automatically.&rdquo;
                </p>
                <div className="text-sm text-green-400">- Alex Thompson, Head of Operations</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 py-20">
        <div className="container mx-auto px-6 text-center">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Ready to Transform Your Community?
            </h2>
            <p className="text-xl mb-8 text-blue-100">
              Join thousands of community managers who&rsquo;ve already upgraded to WaddleBot
            </p>
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <a
                href="https://github.com/WaddleBot/WaddleBot"
                className="px-10 py-5 bg-white text-blue-600 hover:bg-gray-100 rounded-xl text-xl font-semibold transition-colors"
              >
                Get Open Source
              </a>
              <Link
                href="/demo"
                className="px-10 py-5 border-2 border-white/30 hover:bg-white/10 rounded-xl text-xl font-semibold transition-colors"
              >
                Try Cloud Hosted
              </Link>
              <Link
                href="/contact"
                className="px-10 py-5 border-2 border-white/30 hover:bg-white/10 rounded-xl text-xl font-semibold transition-colors"
              >
                Contact Sales
              </Link>
            </div>
            <p className="text-blue-200 text-sm mt-4">
              Free forever • Deploy anywhere • Fair & AGPL3 Licensed • No vendor lock-in
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black/40 backdrop-blur-sm py-16">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="text-2xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                WaddleBot
              </div>
              <p className="text-gray-400 mb-4">
                The future of multi-platform community management
              </p>
              <div className="flex gap-4">
                <a href="https://x.com/penguintechgrp" className="text-gray-400 hover:text-blue-400 transition-colors">
                  X (Twitter)
                </a>
                <a href="https://github.com/WaddleBot" className="text-gray-400 hover:text-blue-400 transition-colors">
                  GitHub
                </a>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <div className="space-y-2 text-gray-400">
                <div><Link href="/features" className="hover:text-white transition-colors">Features</Link></div>
                <div><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></div>
                <div><Link href="/solutions" className="hover:text-white transition-colors">Solutions</Link></div>
                <div><a href="https://docs.waddlebot.io" className="hover:text-white transition-colors">Documentation</a></div>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <div className="space-y-2 text-gray-400">
                <div><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></div>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <div className="space-y-2 text-gray-400">
                <div><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></div>
              </div>
            </div>
          </div>
          <div className="border-t border-white/10 mt-12 pt-8 text-center text-gray-400">
            <p>© 2024 WaddleBot. All rights reserved. Built for the future of community management.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
