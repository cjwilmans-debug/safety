# A+ Content Creator

A React application for generating Amazon A+ content images using the Ideogram AI API. Create stunning product images, lifestyle shots, infographics, and banners for your Amazon listings.

## Features

- **Quick Templates**: Pre-configured prompts for common A+ content types
  - Product Hero shots
  - Lifestyle photography
  - Infographics
  - Comparison layouts
  - Feature grids
  - A+ Banners

- **Customization Options**
  - Multiple aspect ratios (1:1, 16:9, 4:3, 3:2)
  - Various image styles (Realistic, Design, 3D Render, Anime)
  - Custom prompts for fine-tuned control

- **Easy Export**
  - One-click image download
  - Copy image URLs directly

## Prerequisites

- Node.js 18+ installed
- An Ideogram API key ([Get one here](https://ideogram.ai/manage-api))

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/aplus-content-creator.git
   cd aplus-content-creator
   ```

2. **Install dependencies**
   ```bash
   # Install frontend dependencies
   npm install

   # Install server dependencies
   cd server
   npm install
   cd ..
   ```

3. **Configure environment variables**
   ```bash
   # Copy the example env file
   cp .env.example .env

   # Edit .env and add your Ideogram API key
   # IDEOGRAM_API_KEY=your_actual_api_key_here
   ```

4. **Start the application**
   ```bash
   # Start both frontend and backend
   npm start

   # Or run them separately:
   # Terminal 1 - Start the proxy server
   npm run server

   # Terminal 2 - Start the React app
   npm run dev
   ```

5. **Open in browser**

   Visit [http://localhost:3000](http://localhost:3000)

## Project Structure

```
aplus-content-creator/
├── public/              # Static assets
├── server/              # Ideogram API proxy server
│   ├── index.js         # Express server with API endpoints
│   └── package.json     # Server dependencies
├── src/                 # React application source
│   ├── App.jsx          # Main application component
│   ├── main.jsx         # React entry point
│   └── index.css        # Application styles
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── index.html           # HTML entry point
├── package.json         # Frontend dependencies
├── vite.config.js       # Vite configuration
└── README.md            # This file
```

## API Endpoints

The proxy server exposes the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/generate` | POST | Generate images from prompt |
| `/api/upscale` | POST | Upscale an existing image |
| `/api/remix` | POST | Remix an image with new prompt |

## Usage Tips

1. **Start with a template** - Select a template that matches your content type, then customize
2. **Be specific** - Include product details, colors, materials, and mood in your descriptions
3. **Iterate** - Generate multiple variations and pick the best ones
4. **Use appropriate aspect ratios** - 1:1 for main images, 16:9 for banners

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IDEOGRAM_API_KEY` | Your Ideogram API key | Required |
| `PORT` | Proxy server port | 3001 |

## Development

```bash
# Run frontend in development mode
npm run dev

# Run server in development mode with auto-reload
cd server && npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## License

MIT
