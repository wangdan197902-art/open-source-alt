# Open Source Alternatives

> Open Source Software Alternatives Finder

## Deployment

- **Production URL**: https://open-source-alt.pages.dev/
- **GitHub Repo**: https://github.com/wangdan197902-art/open-source-alt
- **Cloudflare Project**: open-source-alt

## Local Development

```bash
# Install Hugo (macOS)
brew install hugo

# Run dev server
hugo server -D

# Build for production
hugo --minify --baseURL "https://open-source-alt.pages.dev/"
```

## Auto Deploy

Push to `main` branch → GitHub Actions auto-deploys to Cloudflare Pages.

## Project Structure

```
├── content/           # Markdown content
├── layouts/           # Hugo templates
├── static/            # Static assets (images, CSS)
├── data/              # JSON data files
├── hugo.toml          # Hugo config
├── wrangler.toml      # Cloudflare Pages config
└── .github/workflows/ # CI/CD
```
