import { useEffect, useRef } from 'react'

const SYMBOLS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

function PatternCanvas({ pattern, paletteUsed, size }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !pattern) return

    const ctx = canvas.getContext('2d')
    const cellSize = 12
    const w = size.width * cellSize
    const h = size.height * cellSize
    canvas.width = w
    canvas.height = h

    // Build symbol map
    const symbolMap = {}
    if (paletteUsed) {
      paletteUsed.forEach((entry, i) => {
        symbolMap[entry.code] = entry.symbol || SYMBOLS[i % SYMBOLS.length]
      })
    }

    // Draw cells
    for (let y = 0; y < size.height; y++) {
      for (let x = 0; x < size.width; x++) {
        const cell = pattern[y]?.[x]
        if (!cell) continue

        const px = x * cellSize
        const py = y * cellSize

        // Fill color
        ctx.fillStyle = cell.hex || '#ffffff'
        ctx.fillRect(px, py, cellSize, cellSize)

        // Draw symbol
        if (cell.code !== '_EMPTY_') {
          const sym = symbolMap[cell.code] || '?'
          ctx.fillStyle = getContrastColor(cell.hex)
          ctx.font = `${cellSize - 4}px monospace`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(sym, px + cellSize / 2, py + cellSize / 2)
        }

        // Grid lines
        ctx.strokeStyle = '#e5e7eb'
        ctx.lineWidth = 0.5
        ctx.strokeRect(px, py, cellSize, cellSize)
      }
    }

    // Crosshair every 10 cells
    ctx.strokeStyle = '#9ca3af'
    ctx.lineWidth = 1.5
    for (let x = 0; x <= size.width; x += 10) {
      ctx.beginPath()
      ctx.moveTo(x * cellSize, 0)
      ctx.lineTo(x * cellSize, h)
      ctx.stroke()
    }
    for (let y = 0; y <= size.height; y += 10) {
      ctx.beginPath()
      ctx.moveTo(0, y * cellSize)
      ctx.lineTo(w, y * cellSize)
      ctx.stroke()
    }
  }, [pattern, paletteUsed, size])

  return <canvas ref={canvasRef} className="border border-gray-300 rounded" style={{ imageRendering: 'pixelated', maxWidth: '100%', height: 'auto' }} />
}

function getContrastColor(hex) {
  if (!hex) return '#000'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#000' : '#fff'
}

export default PatternCanvas
