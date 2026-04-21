import { useState, useRef, useCallback, useEffect } from 'react'
import { Button, Space, Tooltip } from 'antd'
import { ZoomInOutlined, ZoomOutOutlined, CompressOutlined, DownloadOutlined } from '@ant-design/icons'

function PatternCanvas({ pattern, paletteUsed, size }) {
  const containerRef = useRef(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [containerSize, setContainerSize] = useState({ width: 800, height: 500 })
  const dragStart = useRef({ x: 0, y: 0 })

  // Base cell size 24px (competitor uses 32px)
  const baseCellSize = 24
  const cellSize = baseCellSize * zoom
  // Label area for row/column numbers
  const labelSize = Math.max(32, cellSize * 1.2)
  const gridWidth = size.width * cellSize
  const gridHeight = size.height * cellSize

  const labelMap = {}
  if (paletteUsed) {
    paletteUsed.forEach((entry) => { labelMap[entry.code] = entry.code })
  }

  // Observe container size
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerSize({ width: entry.contentRect.width, height: entry.contentRect.height })
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Auto-fit on mount
  useEffect(() => {
    if (containerSize.width === 0) return
    const aw = containerSize.width - 60
    const ah = containerSize.height - 60
    const sx = aw / (size.width * baseCellSize + labelSize)
    const sy = ah / (size.height * baseCellSize + labelSize)
    setZoom(Math.min(sx, sy, 2))
    setPan({ x: 0, y: 0 })
  }, [size.width, size.height, labelSize, containerSize])

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setZoom((p) => Math.min(5, Math.max(0.2, p + delta)))
    setPan({ x: 0, y: 0 })
  }, [])

  const handleMouseDown = useCallback((e) => {
    if (e.button === 0) {
      setIsDragging(true)
      dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    }
  }, [pan])

  const handleMouseMove = useCallback((e) => {
    if (isDragging) setPan({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y })
  }, [isDragging])

  const handleMouseUp = useCallback(() => setIsDragging(false), [])

  const zoomIn = () => setZoom((p) => Math.min(5, p + 0.25))
  const zoomOut = () => setZoom((p) => Math.max(0.2, p - 0.25))
  const fitToScreen = () => {
    if (!containerRef.current) return
    const aw = containerSize.width - 60
    const ah = containerSize.height - 60
    const sx = aw / (size.width * baseCellSize + labelSize)
    const sy = ah / (size.height * baseCellSize + labelSize)
    setZoom(Math.min(sx, sy, 2))
    setPan({ x: 0, y: 0 })
  }

  // Download at native resolution (32px cells)
  const handleDownload = () => {
    const cs = 32
    const ls = 40
    const canvas = document.createElement('canvas')
    canvas.width = size.width * cs + ls
    canvas.height = size.height * cs + ls
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    for (let y = 0; y < size.height; y++) {
      for (let x = 0; x < size.width; x++) {
        const cell = pattern[y]?.[x]
        if (!cell) continue
        const px = x * cs + ls
        const py = y * cs + ls
        ctx.fillStyle = cell.hex || '#f8f8f8'
        ctx.fillRect(px, py, cs, cs)
        if (cell.code !== '_EMPTY_') {
          const label = labelMap[cell.code] || ''
          if (label) {
            ctx.fillStyle = getContrastColor(cell.hex)
            ctx.font = `bold ${cs - 8}px monospace`
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(label, px + cs / 2, py + cs / 2)
          }
        }
        ctx.strokeStyle = '#e5e7eb'
        ctx.lineWidth = 0.5
        ctx.strokeRect(px, py, cs, cs)
      }
    }
    const link = document.createElement('a')
    link.download = `pixelbeans-${size.width}x${size.height}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }

  // Build SVG content — vector text, always crisp at any zoom
  const svgContent = []
  for (let y = 0; y < size.height; y++) {
    for (let x = 0; x < size.width; x++) {
      const cell = pattern[y]?.[x]
      if (!cell) continue
      const px = x * cellSize + labelSize
      const py = y * cellSize + labelSize
      const textColor = getContrastColor(cell.hex)
      svgContent.push(
        <rect key={`c-${x}-${y}`} x={px} y={py} width={cellSize} height={cellSize} fill={cell.hex || '#f8f8f8'} stroke="rgba(0,0,0,0.08)" strokeWidth={Math.max(0.5, cellSize * 0.03)} />,
      )
      if (cell.code !== '_EMPTY_' && labelMap[cell.code]) {
        const fontSize = Math.max(7, cellSize * 0.45)
        svgContent.push(
          <text key={`t-${x}-${y}`} x={px + cellSize / 2} y={py + cellSize / 2} fill={textColor} fontSize={fontSize} fontFamily="monospace" fontWeight="bold" textAnchor="middle" dominantBaseline="central">{labelMap[cell.code]}</text>,
        )
      }
    }
  }

  // Column number labels (every 5th)
  const colLabels = []
  for (let x = 0; x < size.width; x++) {
    if ((x + 1) % 5 === 0 || x === 0) {
      colLabels.push(
        <text key={`cl-${x}`} x={x * cellSize + labelSize + cellSize / 2} y={labelSize / 2 - 4} fill="#94a3b8" fontSize={Math.max(9, cellSize * 0.35)} fontFamily="monospace" textAnchor="middle">{x + 1}</text>,
      )
    }
  }
  // Row number labels (every 5th)
  const rowLabels = []
  for (let y = 0; y < size.height; y++) {
    if ((y + 1) % 5 === 0 || y === 0) {
      rowLabels.push(
        <text key={`rl-${y}`} x={labelSize / 2 - 4} y={y * cellSize + labelSize + cellSize / 2} fill="#94a3b8" fontSize={Math.max(9, cellSize * 0.35)} fontFamily="monospace" textAnchor="middle">{y + 1}</text>,
      )
    }
  }

  // Crosshair lines every 10 cells
  const crosshairs = []
  for (let x = 0; x <= size.width; x += 10) {
    crosshairs.push(<line key={`vh-${x}`} x1={x * cellSize + labelSize} y1={labelSize} x2={x * cellSize + labelSize} y2={labelSize + gridHeight} stroke="rgba(0,0,0,0.18)" strokeWidth={Math.max(1.2, cellSize * 0.05)} />)
  }
  for (let y = 0; y <= size.height; y += 10) {
    crosshairs.push(<line key={`hv-${y}`} x1={labelSize} y1={y * cellSize + labelSize} x2={labelSize + gridWidth} y2={y * cellSize + labelSize} stroke="rgba(0,0,0,0.18)" strokeWidth={Math.max(1.2, cellSize * 0.05)} />)
  }

  const svgW = size.width * cellSize + labelSize
  const svgH = size.height * cellSize + labelSize

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex items-center gap-2 w-full justify-between px-2 py-1.5 bg-gray-50 rounded-lg border border-gray-100">
        <Space size="small">
          <Tooltip title="放大"><Button size="small" icon={<ZoomInOutlined />} onClick={zoomIn} disabled={zoom >= 5} /></Tooltip>
          <Tooltip title="缩小"><Button size="small" icon={<ZoomOutOutlined />} onClick={zoomOut} disabled={zoom <= 0.2} /></Tooltip>
          <Tooltip title="适应窗口"><Button size="small" icon={<CompressOutlined />} onClick={fitToScreen} /></Tooltip>
          <span className="text-xs text-gray-400 font-mono w-12 text-center">{Math.round(zoom * 100)}%</span>
        </Space>
        <Tooltip title="下载 PNG"><Button size="small" icon={<DownloadOutlined />} onClick={handleDownload}>下载</Button></Tooltip>
      </div>

      <div ref={containerRef} className="w-full overflow-hidden rounded-lg cursor-grab active:cursor-grabbing border border-gray-200 bg-white" style={{ height: '55vh' }} onWheel={handleWheel} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        <div style={{ width: '100%', height: '100%', overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width={svgW} height={svgH} style={{ transform: `translate(${pan.x}px, ${pan.y}px)`, transition: isDragging ? 'none' : 'transform 0.15s ease', flexShrink: 0 }}>
            {svgContent}
            {crosshairs}
            {colLabels}
            {rowLabels}
          </svg>
        </div>
      </div>
    </div>
  )
}

function getContrastColor(hex) {
  if (!hex) return '#000'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.55 ? '#1a1a1a' : '#ffffff'
}

export default PatternCanvas
