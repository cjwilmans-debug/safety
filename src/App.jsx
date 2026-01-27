import { useState } from 'react'

const TEMPLATES = [
  { id: 'product-hero', name: 'Product Hero', prompt: 'Professional product photography, hero shot, white background, studio lighting' },
  { id: 'lifestyle', name: 'Lifestyle', prompt: 'Lifestyle product photography, natural setting, warm lighting, aspirational' },
  { id: 'infographic', name: 'Infographic', prompt: 'Clean infographic style, modern design, data visualization, professional' },
  { id: 'comparison', name: 'Comparison', prompt: 'Side by side comparison layout, clear contrast, professional presentation' },
  { id: 'features', name: 'Features Grid', prompt: 'Feature showcase grid, icons and imagery, clean layout, modern design' },
  { id: 'banner', name: 'A+ Banner', prompt: 'Amazon A+ content banner, premium look, brand-focused, high quality' },
]

const ASPECT_RATIOS = [
  { id: '1:1', name: 'Square (1:1)' },
  { id: '16:9', name: 'Widescreen (16:9)' },
  { id: '4:3', name: 'Standard (4:3)' },
  { id: '3:2', name: 'Photo (3:2)' },
]

const STYLES = [
  { id: 'realistic', name: 'Realistic' },
  { id: 'design', name: 'Design' },
  { id: 'render_3d', name: '3D Render' },
  { id: 'anime', name: 'Anime' },
]

function App() {
  const [productName, setProductName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [aspectRatio, setAspectRatio] = useState('1:1')
  const [style, setStyle] = useState('realistic')
  const [customPrompt, setCustomPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [images, setImages] = useState([])
  const [error, setError] = useState('')

  const buildPrompt = () => {
    let prompt = ''

    if (selectedTemplate) {
      const template = TEMPLATES.find(t => t.id === selectedTemplate)
      prompt = template ? template.prompt + ', ' : ''
    }

    if (productName) {
      prompt += `${productName}, `
    }

    if (description) {
      prompt += `${description}, `
    }

    if (customPrompt) {
      prompt += customPrompt
    }

    return prompt.trim().replace(/,\s*$/, '')
  }

  const generateImages = async () => {
    const prompt = buildPrompt()

    if (!prompt) {
      setError('Please provide a product name, description, or custom prompt')
      return
    }

    setLoading(true)
    setError('')
    setImages([])

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          aspect_ratio: aspectRatio,
          style_type: style,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate images')
      }

      setImages(data.images || [])
    } catch (err) {
      setError(err.message || 'An error occurred while generating images')
    } finally {
      setLoading(false)
    }
  }

  const downloadImage = async (url, index) => {
    try {
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `aplus-content-${index + 1}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const copyImageUrl = (url) => {
    navigator.clipboard.writeText(url)
  }

  return (
    <div className="app">
      <header className="header">
        <h1>A+ Content Creator</h1>
        <p>Generate stunning Amazon A+ content images with AI</p>
      </header>

      <div className="content-creator">
        <div className="templates">
          <label>Quick Templates</label>
          <div className="template-chips">
            {TEMPLATES.map(template => (
              <button
                key={template.id}
                className={`template-chip ${selectedTemplate === template.id ? 'active' : ''}`}
                onClick={() => setSelectedTemplate(
                  selectedTemplate === template.id ? null : template.id
                )}
              >
                {template.name}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="productName">Product Name</label>
          <input
            id="productName"
            type="text"
            placeholder="e.g., Premium Wireless Headphones"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Product Description</label>
          <textarea
            id="description"
            placeholder="Describe your product, key features, and the mood you want to convey..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="aspectRatio">Aspect Ratio</label>
            <select
              id="aspectRatio"
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
            >
              {ASPECT_RATIOS.map(ratio => (
                <option key={ratio.id} value={ratio.id}>{ratio.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="style">Style</label>
            <select
              id="style"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
            >
              {STYLES.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="customPrompt">Custom Prompt (Optional)</label>
          <textarea
            id="customPrompt"
            placeholder="Add any additional details or specific instructions..."
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
          />
        </div>

        <button
          className="generate-btn"
          onClick={generateImages}
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate A+ Content Images'}
        </button>

        {error && <div className="error">{error}</div>}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Creating your A+ content images...</p>
          </div>
        )}

        {images.length > 0 && (
          <div className="results">
            <h2>Generated Images</h2>
            <div className="image-grid">
              {images.map((image, index) => (
                <div key={index} className="image-card">
                  <img src={image.url} alt={`Generated A+ content ${index + 1}`} />
                  <div className="image-card-actions">
                    <button
                      className="download-btn"
                      onClick={() => downloadImage(image.url, index)}
                    >
                      Download
                    </button>
                    <button
                      className="copy-btn"
                      onClick={() => copyImageUrl(image.url)}
                    >
                      Copy URL
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
