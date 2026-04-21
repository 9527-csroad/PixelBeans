import { useState, useEffect, useCallback } from 'react'
import { Upload, Slider, InputNumber, Select, Button, Table, Tabs, message, Spin, Card, Row, Col, Space, Tag } from 'antd'
import { InboxOutlined, PictureOutlined, ThunderboltOutlined, FileTextOutlined } from '@ant-design/icons'
import axios from 'axios'
import PatternCanvas from './components/PatternCanvas'

const { Dragger } = Upload

const API_BASE = '/api/v1'

function App() {
  const [file, setFile] = useState(null)
  const [filePreview, setFilePreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  // Params
  const [width, setWidth] = useState(58)
  const [height, setHeight] = useState(58)
  const [palette, setPalette] = useState('mard')
  const [maxColors, setMaxColors] = useState(null)
  const [brightness, setBrightness] = useState(1.0)
  const [contrast, setContrast] = useState(1.0)
  const [saturation, setSaturation] = useState(1.0)
  const [removeIsolated, setRemoveIsolated] = useState(true)

  const [palettes, setPalettes] = useState([])

  useEffect(() => {
    axios.get(`${API_BASE}/palettes`).then(r => setPalettes(r.data))
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!file) {
      message.warning('请先上传图片')
      return
    }
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('image', file)
      formData.append('width', width)
      formData.append('height', height)
      formData.append('palette', palette)
      if (maxColors) formData.append('max_colors', maxColors)
      formData.append('brightness', brightness)
      formData.append('contrast', contrast)
      formData.append('saturation', saturation)
      formData.append('remove_isolated', removeIsolated)

      const resp = await axios.post(`${API_BASE}/pattern`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      })
      setResult(resp.data)
      message.success('生成成功')
    } catch (err) {
      message.error(`生成失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }, [file, width, height, palette, maxColors, brightness, contrast, saturation, removeIsolated])

  const beforeUpload = (f) => {
    setFile(f)
    setFilePreview(URL.createObjectURL(f))
    setResult(null)
    return false
  }

  const bomColumns = [
    { title: '色号', dataIndex: 'code', key: 'code', width: 80, sorter: (a, b) => a.code.localeCompare(b.code) },
    { title: '颜色', dataIndex: 'hex', key: 'hex', width: 60, render: (hex) => <div className="w-6 h-6 rounded border border-gray-300" style={{ backgroundColor: hex }} /> },
    { title: '色名', dataIndex: 'name', key: 'name', width: 80 },
    { title: '符号', dataIndex: 'symbol', key: 'symbol', width: 60 },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80, sorter: (a, b) => a.count - b.count, defaultSortOrder: 'descend', sortDirections: ['descend', 'ascend'] },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">PixelBeans — 拼豆图纸生成器</h1>
          <p className="text-sm text-gray-500 mt-1">上传图片，一键生成专业拼豆图纸</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <Row gutter={[16, 16]}>
          {/* Left: Upload + Params */}
          <Col xs={24} md={8}>
            <Space direction="vertical" className="w-full" size="large">
              {/* Upload */}
              <Card title={<><InboxOutlined /> 上传图片</>} size="small">
                <Dragger beforeUpload={beforeUpload} showUploadList={false} accept="image/*">
                  <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                  <p className="ant-upload-text">点击或拖拽上传图片</p>
                  <p className="ant-upload-hint">支持 JPG / PNG 格式</p>
                </Dragger>
                {filePreview && (
                  <div className="mt-3 text-center">
                    <img src={filePreview} alt="preview" className="max-h-48 mx-auto rounded border" />
                    <p className="text-xs text-gray-400 mt-1">{file?.name}</p>
                  </div>
                )}
              </Card>

              {/* Params */}
              <Card title={<><ThunderboltOutlined /> 参数设置</>} size="small">
                <Space direction="vertical" className="w-full" size="middle">
                  <div>
                    <label className="text-sm text-gray-600">色卡品牌</label>
                    <Select value={palette} onChange={setPalette} className="w-full mt-1" options={palettes.map(p => ({ label: p.toUpperCase(), value: p }))} />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">网格尺寸</label>
                    <Space className="mt-1">
                      <InputNumber value={width} onChange={v => setWidth(v)} min={10} max={200} addonBefore="宽" />
                      <span>×</span>
                      <InputNumber value={height} onChange={v => setHeight(v)} min={10} max={200} addonBefore="高" />
                    </Space>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">最大颜色数</label>
                    <InputNumber value={maxColors} onChange={v => setMaxColors(v)} min={1} max={100} placeholder="不限制" className="w-full mt-1" />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">亮度 {brightness.toFixed(1)}</label>
                    <Slider value={brightness} onChange={setBrightness} min={0.5} max={1.5} step={0.1} />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">对比度 {contrast.toFixed(1)}</label>
                    <Slider value={contrast} onChange={setContrast} min={0.5} max={1.5} step={0.1} />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">饱和度 {saturation.toFixed(1)}</label>
                    <Slider value={saturation} onChange={setSaturation} min={0.5} max={1.5} step={0.1} />
                  </div>
                  <Button type="primary" size="large" block onClick={handleGenerate} loading={loading}>
                    生成图纸
                  </Button>
                </Space>
              </Card>
            </Space>
          </Col>

          {/* Right: Preview + BOM */}
          <Col xs={24} md={16}>
            <Spin spinning={loading} tip="生成中...">
              {result ? (
                <Space direction="vertical" className="w-full" size="large">
                  {/* Stats */}
                  <div className="flex gap-2">
                    <Tag color="blue">网格: {result.size.width}×{result.size.height}</Tag>
                    <Tag color="green">颜色: {result.stats.unique_colors}</Tag>
                    <Tag color="orange">总豆数: {result.stats.total_beads}</Tag>
                  </div>

                  {/* Preview Tabs */}
                  <Card title={<><PictureOutlined /> 预览</>} size="small">
                    <Tabs
                      defaultActiveKey="pattern"
                      items={[
                        { key: 'pattern', label: '拼豆图纸', children: <PatternCanvas pattern={result.pattern} paletteUsed={result.paletteUsed} size={result.size} /> },
                        { key: 'preview', label: '效果预览', children: <img src={`data:image/png;base64,${result.preview_png}`} className="max-w-full rounded" /> },
                        { key: 'grid', label: '符号图纸', children: <img src={`data:image/png;base64,${result.grid_png}`} className="max-w-full rounded" /> },
                      ]}
                    />
                  </Card>

                  {/* BOM */}
                  <Card title={<><FileTextOutlined /> BOM 清单</>} size="small">
                    <Table columns={bomColumns} dataSource={result.palette_used} rowKey="code" size="small" pagination={false} />
                  </Card>
                </Space>
              ) : (
                <div className="bg-white rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center" style={{ height: 400 }}>
                  <p className="text-gray-400">上传图片并点击"生成图纸"后，这里将显示预览结果</p>
                </div>
              )}
            </Spin>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default App
