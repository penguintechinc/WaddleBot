import Link from 'next/link';

export default function Pricing() {
  return (
    <div className="font-sans min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center p-6 bg-black/20 backdrop-blur-sm sticky top-0 z-50">
        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          WaddleBot
        </Link>
        <div className="hidden md:flex gap-8">
          <Link href="/features" className="hover:text-blue-300 transition-colors">Features</Link>
          <Link href="/pricing" className="text-blue-300">Pricing</Link>
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
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-gray-200">
            Choose the plan that scales with your community. No hidden fees, no surprises.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="container mx-auto px-6 pb-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            
            {/* Open Source Plan */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <span className="bg-gradient-to-r from-green-500 to-blue-500 text-white px-4 py-2 rounded-full text-sm font-semibold">
                  Default Option
                </span>
              </div>
              
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold mb-4 text-green-300">Open Source</h3>
                <div className="mb-4">
                  <span className="text-5xl font-bold">Free</span>
                  <span className="text-gray-400 text-lg">/forever</span>
                </div>
                <p className="text-gray-300">
                  Perfect for developers and self-hosted communities. Full control over your bot.
                </p>
              </div>

              <div className="space-y-4 mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Complete source code access</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Self-hosted deployment</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Multi-platform support</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>All core interaction modules</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Docker & Kubernetes support</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Community forum support</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Unlimited channels</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Fair & AGPL3 License - modify freely</span>
                </div>
              </div>

              <a
                href="https://github.com/WaddleBot/WaddleBot"
                className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-105 text-center block"
              >
                Get Started on GitHub
              </a>
              <p className="text-center text-gray-400 text-sm mt-3">
                No registration required • Deploy anywhere
              </p>
            </div>

            {/* Cloud Hosted Plan */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8">
              
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold mb-4 text-blue-300">Cloud Hosted</h3>
                <div className="mb-4">
                  <span className="text-5xl font-bold">$2</span>
                  <span className="text-gray-400 text-lg">/channel/month</span>
                </div>
                <p className="text-gray-300">
                  Skip the hosting hassle. We manage everything for you.
                </p>
              </div>

              <div className="space-y-4 mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Everything in Open Source</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Fully managed hosting</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Automatic updates & patches</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>99.9% uptime SLA</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Automated backups</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Priority email support</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Advanced monitoring & alerts</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>One-click setup</span>
                </div>
              </div>

              <Link
                href="/demo"
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-105 text-center block"
              >
                Start Free Trial
              </Link>
              <p className="text-center text-gray-400 text-sm mt-3">
                14-day free trial • No credit card required
              </p>
            </div>

            {/* Enterprise/Embedded Plan */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8">
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold mb-4 text-purple-300">Enterprise Embedded</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold">Custom</span>
                </div>
                <p className="text-gray-300">
                  Self-hosted solution with full customization and white-label options.
                </p>
              </div>

              <div className="space-y-4 mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Everything in Cloud Hosted</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Self-hosted deployment</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>White-label customization</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Custom integrations & APIs</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Dedicated infrastructure</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>24/7 dedicated support</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Custom SLA agreements</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span>Professional services</span>
                </div>
              </div>

              <Link
                href="/contact"
                className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all text-center block"
              >
                Contact Sales
              </Link>
              <p className="text-center text-gray-400 text-sm mt-3">
                Custom pricing based on requirements
              </p>
            </div>
          </div>

          {/* Marketplace Notice */}
          <div className="bg-gradient-to-r from-orange-500/20 to-yellow-500/20 border border-orange-500/30 rounded-xl p-6 mb-8">
            <div className="flex items-start gap-4">
              <div className="text-orange-400 text-2xl">💰</div>
              <div>
                <h3 className="text-lg font-bold mb-2 text-orange-300">Marketplace Modules</h3>
                <p className="text-gray-300 mb-2">
                  While WaddleBot&rsquo;s core features are included in your plan, some specialized modules from our marketplace may require additional subscriptions or one-time payments.
                </p>
                <div className="text-sm text-gray-400">
                  Examples include premium AI models, advanced analytics packages, or third-party integrations developed by our community partners.
                </div>
              </div>
            </div>
          </div>

          {/* Volume Pricing */}
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 text-center">
            <h3 className="text-2xl font-bold mb-4">Volume Discounts Available</h3>
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <div className="text-2xl font-bold text-green-400 mb-2">10+ channels</div>
                <div className="text-gray-400">15% discount</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-400 mb-2">50+ channels</div>
                <div className="text-gray-400">25% discount</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-400 mb-2">100+ channels</div>
                <div className="text-gray-400">35% discount</div>
              </div>
            </div>
            <p className="text-gray-300 mt-6">
              Discounts are automatically applied to your billing. Need a custom plan? 
              <Link href="/contact" className="text-blue-400 hover:text-blue-300 ml-1">Contact us</Link>
            </p>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="bg-black/20 backdrop-blur-sm py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-16">
              Frequently Asked Questions
            </h2>
            
            <div className="space-y-8">
              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">What counts as a &ldquo;channel&rdquo;?</h3>
                <p className="text-gray-300">
                  A channel is any individual Discord channel, Twitch stream, or Slack channel where WaddleBot is active. For Discord servers, each text channel counts separately. For Twitch, each stream channel counts as one. For Slack, each workspace channel counts as one.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">Can I switch between plans?</h3>
                <p className="text-gray-300">
                  Yes! You can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle. Contact support if you need immediate plan changes.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">What&rsquo;s included in the free trial?</h3>
                <p className="text-gray-300">
                  The 14-day free trial includes full access to all Cloud Hosted features for up to 3 channels. No credit card required. You can test all core functionality before deciding to subscribe.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">Do marketplace modules cost extra?</h3>
                <p className="text-gray-300">
                  Core WaddleBot modules are included in your plan. However, some specialized modules from our community marketplace may require additional one-time purchases or subscriptions. These are clearly marked in the marketplace with their pricing.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">What are the main differences between the plans?</h3>
                <p className="text-gray-300">
                  <strong>Open Source:</strong> Full source code, self-hosted, unlimited use, community support.<br/>
                  <strong>Cloud Hosted:</strong> Managed hosting, automatic updates, 99.9% uptime SLA, priority support.<br/>
                  <strong>Enterprise Embedded:</strong> White-labeling, custom integrations, dedicated infrastructure, 24/7 support.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">Why should I choose the open source version?</h3>
                <p className="text-gray-300">
                  The open source version gives you complete control, unlimited scaling, no vendor lock-in, and zero ongoing costs. Perfect if you have technical expertise and want to customize the platform or deploy on your own infrastructure.
                </p>
              </div>

              <div className="bg-white/5 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-3 text-blue-300">Is there a setup fee?</h3>
                <p className="text-gray-300">
                  No setup fees for Open Source (free forever) or Cloud Hosted plans. Enterprise Embedded may include professional services for custom deployment and configuration, priced separately based on requirements.
                </p>
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
              Ready to Get Started?
            </h2>
            <p className="text-xl mb-8 text-blue-100">
              Join thousands of communities already using WaddleBot
            </p>
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <a
                href="https://github.com/WaddleBot/WaddleBot"
                className="px-10 py-5 bg-green-600 hover:bg-green-700 text-white rounded-xl text-xl font-semibold transition-colors"
              >
                Get Open Source
              </a>
              <Link
                href="/demo"
                className="px-10 py-5 bg-white text-blue-600 hover:bg-gray-100 rounded-xl text-xl font-semibold transition-colors"
              >
                Start Free Trial
              </Link>
              <Link
                href="/contact"
                className="px-10 py-5 border-2 border-white/30 hover:bg-white/10 rounded-xl text-xl font-semibold transition-colors"
              >
                Contact Sales
              </Link>
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