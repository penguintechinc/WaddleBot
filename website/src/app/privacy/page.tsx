import Link from 'next/link';

export default function Privacy() {
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
          <Link href="/contact" className="hover:text-blue-300 transition-colors">Contact</Link>
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
            Privacy Policy
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-gray-200">
            Your privacy matters to us. Here&rsquo;s how we handle your data.
          </p>
        </div>
      </section>

      {/* Privacy Policy Content */}
      <section className="container mx-auto px-6 pb-20">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10 space-y-8">
            
            {/* Last Updated */}
            <div className="text-center pb-6 border-b border-white/10">
              <p className="text-gray-400">Last updated: August 26, 2024</p>
            </div>

            {/* Introduction */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Introduction</h2>
              <p className="text-gray-300 leading-relaxed">
                WaddleBot (&ldquo;we,&rdquo; &ldquo;our,&rdquo; or &ldquo;us&rdquo;) respects your privacy and is committed to protecting your personal data. This privacy policy explains how we collect, use, and safeguard your information when you use our open source community management platform.
              </p>
            </div>

            {/* Data We Collect */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Information We Collect</h2>
              <div className="space-y-4">
                <div>
                  <h3 className="text-xl font-semibold mb-2 text-purple-300">Open Source Usage</h3>
                  <p className="text-gray-300 leading-relaxed">
                    When you use the open source version of WaddleBot self-hosted on your infrastructure, we do not collect any personal data. All data remains on your systems under your control.
                  </p>
                </div>
                
                <div>
                  <h3 className="text-xl font-semibold mb-2 text-purple-300">Cloud Hosted Service</h3>
                  <p className="text-gray-300 leading-relaxed mb-3">
                    For our cloud hosted service, we may collect:
                  </p>
                  <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                    <li>Account information (email, name, organization)</li>
                    <li>Platform connection data (Discord, Slack, Twitch credentials)</li>
                    <li>Community management data (messages, user interactions, commands)</li>
                    <li>Usage analytics and performance metrics</li>
                    <li>Payment information (processed by third-party providers)</li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-2 text-purple-300">Website Analytics</h3>
                  <p className="text-gray-300 leading-relaxed">
                    We may use standard web analytics to understand how visitors use our website, including IP addresses, browser information, and page views.
                  </p>
                </div>
              </div>
            </div>

            {/* How We Use Data */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">How We Use Your Information</h2>
              <p className="text-gray-300 leading-relaxed mb-4">
                We use collected information to:
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>Provide and maintain our cloud hosted services</li>
                <li>Process your transactions and manage your account</li>
                <li>Communicate with you about service updates and support</li>
                <li>Improve our platform and develop new features</li>
                <li>Ensure security and prevent fraud</li>
                <li>Comply with legal obligations</li>
              </ul>
            </div>

            {/* Data Sharing */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Data Sharing</h2>
              <p className="text-gray-300 leading-relaxed mb-4">
                We do not sell, trade, or rent your personal information to third parties. We may share data only in these limited circumstances:
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>With your explicit consent</li>
                <li>To comply with legal requirements or court orders</li>
                <li>With trusted service providers who assist in our operations (under strict confidentiality agreements)</li>
                <li>In connection with a business transfer or acquisition</li>
                <li>To protect our rights, property, or safety, or that of our users</li>
              </ul>
            </div>

            {/* Data Security */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Data Security</h2>
              <p className="text-gray-300 leading-relaxed">
                We implement appropriate technical and organizational security measures to protect your data against unauthorized access, alteration, disclosure, or destruction. This includes encryption, access controls, regular security assessments, and secure data transmission protocols.
              </p>
            </div>

            {/* Data Retention */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Data Retention</h2>
              <p className="text-gray-300 leading-relaxed">
                We retain your personal information only as long as necessary to provide our services and fulfill the purposes outlined in this policy, unless a longer retention period is required by law. When data is no longer needed, we securely delete or anonymize it.
              </p>
            </div>

            {/* Your Rights */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Your Rights</h2>
              <p className="text-gray-300 leading-relaxed mb-4">
                You have the right to:
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li><strong>Access:</strong> Request copies of your personal data</li>
                <li><strong>Rectification:</strong> Request correction of inaccurate data</li>
                <li><strong>Erasure:</strong> Request deletion of your personal data</li>
                <li><strong>Portability:</strong> Request transfer of your data to another service</li>
                <li><strong>Objection:</strong> Object to processing of your personal data</li>
                <li><strong>Restriction:</strong> Request restriction of processing your data</li>
              </ul>
            </div>

            {/* Data Deletion */}
            <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-6">
              <h2 className="text-3xl font-bold mb-4 text-green-300">Data Deletion Policy</h2>
              <p className="text-gray-300 leading-relaxed mb-4">
                <strong>We will delete your data upon request.</strong> To request deletion of your personal data:
              </p>
              <ol className="list-decimal list-inside text-gray-300 space-y-2 ml-4 mb-4">
                <li>Email us at <a href="mailto:sales@penguintech.io?subject=Data Deletion Request" className="text-blue-400 hover:text-blue-300">sales@penguintech.io</a> with &ldquo;Data Deletion Request&rdquo; in the subject line</li>
                <li>Include your account email and specify what data you want deleted</li>
                <li>We will confirm your identity and process the request within 30 days</li>
                <li>You will receive confirmation once the deletion is complete</li>
              </ol>
              <p className="text-gray-300 leading-relaxed">
                Note: Some data may need to be retained for legal compliance or security purposes, but we will inform you of any such exceptions.
              </p>
            </div>

            {/* International Transfers */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">International Data Transfers</h2>
              <p className="text-gray-300 leading-relaxed">
                Your data may be transferred and processed in countries other than your own. We ensure appropriate safeguards are in place to protect your data in accordance with applicable privacy laws.
              </p>
            </div>

            {/* Children's Privacy */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Children&rsquo;s Privacy</h2>
              <p className="text-gray-300 leading-relaxed">
                Our service is not intended for children under 13 years old. We do not knowingly collect personal information from children under 13. If we become aware that we have collected such information, we will take steps to delete it immediately.
              </p>
            </div>

            {/* Changes to Policy */}
            <div>
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Changes to This Policy</h2>
              <p className="text-gray-300 leading-relaxed">
                We may update this privacy policy from time to time. We will notify you of any significant changes by posting the new policy on this page and updating the &ldquo;last updated&rdquo; date. Your continued use of our service after changes become effective constitutes acceptance of the revised policy.
              </p>
            </div>

            {/* Contact Information */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
              <h2 className="text-3xl font-bold mb-4 text-blue-300">Contact Us</h2>
              <p className="text-gray-300 leading-relaxed mb-4">
                If you have questions about this privacy policy or want to exercise your privacy rights, please contact us:
              </p>
              <div className="space-y-2 text-gray-300">
                <p><strong>Email:</strong> <a href="mailto:sales@penguintech.io?subject=Privacy Policy Question" className="text-blue-400 hover:text-blue-300">sales@penguintech.io</a></p>
                <p><strong>Subject Line:</strong> Privacy Policy Question</p>
                <p><strong>Response Time:</strong> We aim to respond within 48 hours</p>
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