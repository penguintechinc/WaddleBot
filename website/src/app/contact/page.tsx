import Link from 'next/link';

export default function Contact() {
  return (
    <div className="font-sans min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center p-6 bg-black/20 backdrop-blur-sm sticky top-0 z-50">
        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          WaddleBot
        </Link>
        <div className="hidden md:flex gap-8">
          <Link href="/features" className="hover:text-blue-300 transition-colors">Features</Link>
          <Link href="/pricing" className="hover:text-blue-300 transition-colors">Pricing</Link>
          <Link href="/solutions" className="hover:text-blue-300 transition-colors">Solutions</Link>
          <a href="https://docs.waddlebot.io" className="hover:text-blue-300 transition-colors">Documentation</a>
          <Link href="/contact" className="text-blue-300">Contact</Link>
        </div>
        <div className="flex gap-4">
          <Link href="/demo" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-semibold">
            Live Demo
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Get in Touch
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-gray-200">
            Ready to transform your community management? Let&rsquo;s talk about how WaddleBot can help.
          </p>
        </div>
      </section>

      {/* Contact Options */}
      <section className="container mx-auto px-6 pb-20">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            
            {/* Sales Inquiries */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center hover:border-blue-500/50 transition-colors">
              <div className="text-4xl mb-4">💼</div>
              <h3 className="text-2xl font-bold mb-4 text-blue-300">Sales & Enterprise</h3>
              <p className="text-gray-300 mb-6">
                Interested in Cloud Hosted or Enterprise solutions? Our sales team can help you find the perfect plan.
              </p>
              <div className="space-y-3 mb-6">
                <div className="text-sm text-gray-400">Perfect for:</div>
                <div className="text-sm">• Large communities (50+ channels)</div>
                <div className="text-sm">• Enterprise deployments</div>
                <div className="text-sm">• Custom integrations</div>
                <div className="text-sm">• White-label solutions</div>
              </div>
              <a
                href="mailto:sales@penguintech.io?subject=WaddleBot Enterprise Inquiry"
                className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              >
                Contact Sales
              </a>
            </div>

            {/* Technical Support */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center hover:border-green-500/50 transition-colors">
              <div className="text-4xl mb-4">🛠️</div>
              <h3 className="text-2xl font-bold mb-4 text-green-300">Technical Support</h3>
              <p className="text-gray-300 mb-6">
                Need help with installation, configuration, or troubleshooting? Our technical team is here to help.
              </p>
              <div className="space-y-3 mb-6">
                <div className="text-sm text-gray-400">We can help with:</div>
                <div className="text-sm">• Installation & setup</div>
                <div className="text-sm">• Configuration issues</div>
                <div className="text-sm">• Performance optimization</div>
                <div className="text-sm">• Custom module development</div>
              </div>
              <a
                href="mailto:sales@penguintech.io?subject=WaddleBot Technical Support Request"
                className="inline-block px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
              >
                Get Support
              </a>
            </div>

            {/* Community & Open Source */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center hover:border-purple-500/50 transition-colors">
              <div className="text-4xl mb-4">🌟</div>
              <h3 className="text-2xl font-bold mb-4 text-purple-300">Community & Open Source</h3>
              <p className="text-gray-300 mb-6">
                Questions about the open source version? Want to contribute? Join our vibrant community of developers.
              </p>
              <div className="space-y-3 mb-6">
                <div className="text-sm text-gray-400">Connect with us:</div>
                <div className="text-sm">• GitHub Discussions</div>
                <div className="text-sm">• Discord Server</div>
                <div className="text-sm">• Community Forums</div>
                <div className="text-sm">• Contribution Guidelines</div>
              </div>
              <a
                href="https://github.com/WaddleBot/WaddleBot/discussions"
                className="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition-colors"
              >
                Join Community
              </a>
            </div>

          </div>

          {/* Contact Form */}
          <div className="max-w-2xl mx-auto bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10">
            <h2 className="text-3xl font-bold mb-6 text-center">Send us a Message</h2>
            <form action="mailto:sales@penguintech.io?subject=WaddleBot Contact Form" method="post" encType="text/plain" className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-semibold mb-2">First Name</label>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder="Your first name"
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-sm font-semibold mb-2">Last Name</label>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                    placeholder="Your last name"
                  />
                </div>
              </div>
              
              <div>
                <label htmlFor="email" className="block text-sm font-semibold mb-2">Email Address</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="your.email@company.com"
                  required
                />
              </div>

              <div>
                <label htmlFor="company" className="block text-sm font-semibold mb-2">Company/Organization</label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="Your company name"
                />
              </div>

              <div>
                <label htmlFor="subject" className="block text-sm font-semibold mb-2">Subject</label>
                <select
                  id="subject"
                  name="subject"
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors"
                  required
                >
                  <option value="">Select a topic</option>
                  <option value="sales">Sales Inquiry</option>
                  <option value="enterprise">Enterprise Solutions</option>
                  <option value="support">Technical Support</option>
                  <option value="partnership">Partnership Opportunity</option>
                  <option value="media">Press & Media</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label htmlFor="message" className="block text-sm font-semibold mb-2">Message</label>
                <textarea
                  id="message"
                  name="message"
                  rows={6}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:border-blue-500 transition-colors resize-vertical"
                  placeholder="Tell us about your community, your needs, or any questions you have..."
                  required
                ></textarea>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="newsletter"
                  name="newsletter"
                  className="w-4 h-4 text-blue-600 bg-white/10 border border-white/20 rounded focus:ring-blue-500"
                />
                <label htmlFor="newsletter" className="text-sm text-gray-300">
                  I&rsquo;d like to receive updates about WaddleBot features and community news
                </label>
              </div>

              <button
                type="submit"
                className="w-full px-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold rounded-lg transition-all transform hover:scale-105"
              >
                Send Message
              </button>
            </form>
          </div>

        </div>
      </section>

      {/* Quick Links */}
      <section className="bg-black/20 backdrop-blur-sm py-16">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">
              Quick Links
            </h2>
            
            <div className="grid md:grid-cols-4 gap-6 text-center">
              <div>
                <h3 className="font-semibold mb-3 text-blue-300">Documentation</h3>
                <div className="space-y-2 text-sm text-gray-400">
                  <div><a href="https://docs.waddlebot.io" className="hover:text-white transition-colors">Getting Started</a></div>
                  <div><a href="https://docs.waddlebot.io/api" className="hover:text-white transition-colors">API Reference</a></div>
                  <div><a href="https://docs.waddlebot.io/guides" className="hover:text-white transition-colors">Deployment Guides</a></div>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold mb-3 text-green-300">Open Source</h3>
                <div className="space-y-2 text-sm text-gray-400">
                  <div><a href="https://github.com/WaddleBot/WaddleBot" className="hover:text-white transition-colors">GitHub Repository</a></div>
                  <div><a href="https://github.com/WaddleBot/WaddleBot/issues" className="hover:text-white transition-colors">Report Issues</a></div>
                  <div><a href="https://github.com/WaddleBot/WaddleBot/discussions" className="hover:text-white transition-colors">Discussions</a></div>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold mb-3 text-purple-300">Community</h3>
                <div className="space-y-2 text-sm text-gray-400">
                  <div><a href="https://discord.gg/waddlebot" className="hover:text-white transition-colors">Discord Server</a></div>
                  <div><a href="https://x.com/penguintechgrp" className="hover:text-white transition-colors">X (Twitter)</a></div>

                  <div><a href="https://reddit.com/r/waddlebot" className="hover:text-white transition-colors">Reddit</a></div>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold mb-3 text-yellow-300">Resources</h3>
                <div className="space-y-2 text-sm text-gray-400">
                  <div><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></div>
                  <div><Link href="/solutions" className="hover:text-white transition-colors">Solutions</Link></div>
                  <div><Link href="/demo" className="hover:text-white transition-colors">Live Demo</Link></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Office Information */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold mb-8">
              We&rsquo;re a Global Team
            </h2>
            <p className="text-xl text-gray-300 mb-12">
              While WaddleBot is open source and distributed, our core team operates remotely with contributors worldwide.
            </p>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white/5 p-6 rounded-xl">
                <div className="text-3xl mb-4">🌍</div>
                <h3 className="font-semibold mb-2">Global Community</h3>
                <p className="text-gray-400 text-sm">Contributors and users from over 50 countries</p>
              </div>
              
              <div className="bg-white/5 p-6 rounded-xl">
                <div className="text-3xl mb-4">⏰</div>
                <h3 className="font-semibold mb-2">24/7 Support</h3>
                <p className="text-gray-400 text-sm">Round-the-clock support through our global team</p>
              </div>
              
              <div className="bg-white/5 p-6 rounded-xl">
                <div className="text-3xl mb-4">💬</div>
                <h3 className="font-semibold mb-2">Multiple Languages</h3>
                <p className="text-gray-400 text-sm">Support available in English, Spanish, French, and German</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black/40 backdrop-blur-sm py-16">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <Link href="/" className="text-2xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent block">
                WaddleBot
              </Link>
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