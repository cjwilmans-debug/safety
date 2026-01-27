import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'

dotenv.config()

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

// Generate images using Ideogram API
app.post('/api/generate', async (req, res) => {
  const { prompt, aspect_ratio = '1:1', style_type = 'realistic' } = req.body

  if (!prompt) {
    return res.status(400).json({ error: 'Prompt is required' })
  }

  const apiKey = process.env.IDEOGRAM_API_KEY

  if (!apiKey) {
    return res.status(500).json({ error: 'Ideogram API key not configured' })
  }

  try {
    const response = await fetch('https://api.ideogram.ai/generate', {
      method: 'POST',
      headers: {
        'Api-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_request: {
          prompt,
          aspect_ratio: aspect_ratio.replace(':', '_'),
          model: 'V_2',
          magic_prompt_option: 'AUTO',
          style_type: style_type.toUpperCase(),
        },
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('Ideogram API error:', data)
      return res.status(response.status).json({
        error: data.message || 'Failed to generate images',
      })
    }

    // Transform response to simplified format
    const images = data.data?.map(item => ({
      url: item.url,
      prompt: item.prompt,
      resolution: item.resolution,
    })) || []

    res.json({ images })
  } catch (error) {
    console.error('Server error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
})

// Upscale image endpoint
app.post('/api/upscale', async (req, res) => {
  const { image_id } = req.body

  if (!image_id) {
    return res.status(400).json({ error: 'Image ID is required' })
  }

  const apiKey = process.env.IDEOGRAM_API_KEY

  if (!apiKey) {
    return res.status(500).json({ error: 'Ideogram API key not configured' })
  }

  try {
    const response = await fetch('https://api.ideogram.ai/upscale', {
      method: 'POST',
      headers: {
        'Api-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_request: {
          image_id,
        },
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('Ideogram API error:', data)
      return res.status(response.status).json({
        error: data.message || 'Failed to upscale image',
      })
    }

    res.json({ image: data.data?.[0] || null })
  } catch (error) {
    console.error('Server error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
})

// Remix image endpoint
app.post('/api/remix', async (req, res) => {
  const { image_url, prompt, aspect_ratio = '1:1', style_type = 'realistic' } = req.body

  if (!image_url || !prompt) {
    return res.status(400).json({ error: 'Image URL and prompt are required' })
  }

  const apiKey = process.env.IDEOGRAM_API_KEY

  if (!apiKey) {
    return res.status(500).json({ error: 'Ideogram API key not configured' })
  }

  try {
    const response = await fetch('https://api.ideogram.ai/remix', {
      method: 'POST',
      headers: {
        'Api-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_request: {
          prompt,
          aspect_ratio: aspect_ratio.replace(':', '_'),
          model: 'V_2',
          magic_prompt_option: 'AUTO',
          style_type: style_type.toUpperCase(),
        },
        image_url,
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('Ideogram API error:', data)
      return res.status(response.status).json({
        error: data.message || 'Failed to remix image',
      })
    }

    const images = data.data?.map(item => ({
      url: item.url,
      prompt: item.prompt,
      resolution: item.resolution,
    })) || []

    res.json({ images })
  } catch (error) {
    console.error('Server error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
})

app.listen(PORT, () => {
  console.log(`Ideogram proxy server running on port ${PORT}`)
})
