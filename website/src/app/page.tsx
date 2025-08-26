export default function Home() {
  return (
    <div className="font-sans min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center p-6 bg-black/20 backdrop-blur-sm">
        <div className="text-2xl font-bold">WaddleBot</div>
        <div className="flex gap-6">
          <a href="/docs" className="hover:text-blue-300 transition-colors">
            Documentation
          </a>
          <a href="https://github.com/WaddleBot" className="hover:text-blue-300 transition-colors" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="container mx-auto px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Multi-Platform Chat Bot System
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-gray-200">
            A modular, microservices architecture for Discord, Twitch, and Slack communities
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="/docs"
              className="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-lg font-semibold transition-colors"
            >
              Get Started
            </a>
            <a
              href="https://github.com/WaddleBot"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 border border-white/30 hover:bg-white/10 rounded-lg text-lg font-semibold transition-colors"
            >
              View on GitHub
            </a>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20 max-w-6xl mx-auto">
          <div className="bg-white/10 backdrop-blur-sm p-6 rounded-xl">
            <h3 className="text-xl font-bold mb-4 text-blue-300">Modular Architecture</h3>
            <p className="text-gray-300">
              Microservices-based design with collector modules for each platform and interaction modules for functionality
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm p-6 rounded-xl">
            <h3 className="text-xl font-bold mb-4 text-purple-300">Multi-Platform</h3>
            <p className="text-gray-300">
              Native support for Discord, Twitch, and Slack with unified command processing and user management
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm p-6 rounded-xl">
            <h3 className="text-xl font-bold mb-4 text-indigo-300">Scalable</h3>
            <p className="text-gray-300">
              Built for scale with Kong API Gateway, PostgreSQL with read replicas, and Kubernetes deployment
            </p>
          </div>
        </div>

        {/* Core Components */}
        <div className="mt-20">
          <h2 className="text-3xl font-bold mb-10">Core Components</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white/5 p-4 rounded-lg">
              <h4 className="font-semibold mb-2">Router Module</h4>
              <p className="text-sm text-gray-400">High-performance command routing with multi-threading and caching</p>
            </div>
            <div className="bg-white/5 p-4 rounded-lg">
              <h4 className="font-semibold mb-2">Marketplace</h4>
              <p className="text-sm text-gray-400">Community module marketplace with subscription management</p>
            </div>
            <div className="bg-white/5 p-4 rounded-lg">
              <h4 className="font-semibold mb-2">Identity Core</h4>
              <p className="text-sm text-gray-400">Cross-platform identity linking and verification system</p>
            </div>
            <div className="bg-white/5 p-4 rounded-lg">
              <h4 className="font-semibold mb-2">Browser Sources</h4>
              <p className="text-sm text-gray-400">OBS integration with WebSocket-powered browser sources</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-black/20 p-6 text-center text-gray-400 mt-20">
        <p>© 2024 WaddleBot. Multi-platform chat bot system for modern communities.</p>
      </footer>
    </div>
  );
}
