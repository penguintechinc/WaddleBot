# WaddleBot Website

The main marketing website for WaddleBot, built with Next.js and deployed to Cloudflare Pages.

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the site locally.

## Deployment

This site is optimized for deployment to Cloudflare Pages with static site generation.

### Automatic Deployment
Connect your repository to Cloudflare Pages with these settings:
- **Build command**: `npm run build`
- **Build output directory**: `out`
- **Root directory**: `website`

### Manual Deployment
For manual deployment with Wrangler CLI:
```bash
# Install Wrangler globally
npm install -g wrangler

# Deploy to Cloudflare Pages
npm run build
wrangler pages publish out --project-name=waddlebot-website
```

## Features

- **Static Site Generation**: Optimized for Cloudflare Pages with `output: 'export'`
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Fast Loading**: Optimized images and static assets
- **SEO Optimized**: Proper meta tags and Open Graph support

## Structure

- `src/app/page.tsx` - Homepage showcasing WaddleBot features
- `src/app/layout.tsx` - Root layout with metadata
- `next.config.js` - Next.js configuration for static export
- `wrangler.toml` - Cloudflare Pages configuration
- `_headers` - HTTP headers for security and caching
- `_redirects` - URL redirects (docs → docs.waddlebot.io)

## Configuration Files

- **`next.config.js`**: Configures Next.js for static export and Cloudflare optimization
- **`wrangler.toml`**: Cloudflare Workers/Pages configuration
- **`_headers`**: Security headers and caching rules
- **`_redirects`**: URL redirections for the site
