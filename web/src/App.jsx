import { useState, useEffect, useCallback } from 'react'
import { ConfigProvider, Upload, Slider, InputNumber, Select, Button, Table, Tabs, message, Spin, Card, Row, Col, Space, Divider, Switch, Tag, Collapse } from 'antd'
import { InboxOutlined, CloudUploadOutlined, SettingOutlined, PictureOutlined, AppstoreOutlined, FileTextOutlined, DownloadOutlined } from '@ant-design/icons'
import axios from 'axios'
import PatternCanvas from './components/PatternCanvas'

const { Dragger } = Upload
const { Panel } = Collapse

const API_BASE = '/api/v1'

// antd teal theme
const antdTheme = {
  token: {
    colorPrimary: '#0D9488',
    borderRadius: 8,
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  },
  components: {
    Button: {
      defaultBg: '#0D9488',
      defaultColor: '#fff',
      primaryColor: '#fff',
    },
    Card: {
      headerPadding: '12px 16px',
    },
    Table: {
      headerBg: '#F0FDFA',
      headerColor: '#0F766E',
      headerSortActiveBg: '#CCFBF1',
    },
    Tabs: {
      itemActiveColor: '#0D9488',
      itemHoverColor: '#14B8A6',
      itemSelectedColor: '#0D9488',
      inkBarColor: '#0D9488',
    },
    Collapse: {
      headerBg: '#fff',
      contentBg: '#fff',
    },
  },
}

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
  const [showAdvanced, setShowAdvanced] = useState(false)

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

  const handleReset = () => {
    setFile(null)
    setFilePreview(null)
    setResult(null)
    setWidth(58)
    setHeight(58)
    setBrightness(1.0)
    setContrast(1.0)
    setSaturation(1.0)
    setMaxColors(null)
    setRemoveIsolated(true)
  }

  const bomColumns = [
    {
      title: '色号',
      dataIndex: 'code',
      key: 'code',
      width: 80,
      fixed: 'left',
      sorter: (a, b) => a.code.localeCompare(b.code),
      render: (code) => <span className="font-mono text-sm font-medium text-teal-700">{code}</span>,
    },
    {
      title: '颜色',
      dataIndex: 'hex',
      key: 'hex',
      width: 50,
      render: (hex) => (
        <div
          className="w-6 h-6 rounded-md border border-gray-200 shadow-sm mx-auto cursor-pointer"
          style={{ backgroundColor: hex }}
          title={hex}
        />
      ),
    },
    {
      title: '色名',
      dataIndex: 'name',
      key: 'name',
      width: 70,
      render: (name) => <span className="text-xs text-gray-500">{name}</span>,
    },
    {
      title: '数量',
      dataIndex: 'count',
      key: 'count',
      width: 80,
      sorter: (a, b) => a.count - b.count,
      defaultSortOrder: 'descend',
      sortDirections: ['descend', 'ascend'],
      render: (count) => <span className="font-medium">{count}</span>,
    },
  ]

  return (
    <ConfigProvider theme={antdTheme}>
      <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #F0FDFA 0%, #FEFCE8 50%, #FFF7ED 100%)' }}>
        {/* Header */}
        <header className="sticky top-0 z-50 backdrop-blur-md" style={{ backgroundColor: 'rgba(240, 253, 250, 0.85)', borderBottom: '1px solid #CCFBF1' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0D9488, #14B8A6)' }}>
                <AppstoreOutlined style={{ color: '#fff', fontSize: 16 }} />
              </div>
              <div>
                <h1 className="text-lg font-bold leading-tight" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: 14, color: '#0F766E' }}>
                  PixelBeans
                </h1>
                <p className="text-xs text-gray-400 hidden sm:block">拼豆图纸生成器</p>
              </div>
            </div>
            {result && (
              <Button size="small" icon={<DownloadOutlined />} onClick={() => message.info('PDF 导出功能开发中')}>
                导出 PDF
              </Button>
            )}
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <Row gutter={[20, 20]}>
            {/* Left: Upload + Params */}
            <Col xs={24} lg={7}>
              <Space direction="vertical" className="w-full" size={16}>
                {/* Upload Card */}
                <Card
                  size="small"
                  className="shadow-sm hover:shadow-md transition-shadow duration-200"
                  styles={{ body: { padding: '12px' } }}
                >
                  <Dragger
                    beforeUpload={beforeUpload}
                    showUploadList={false}
                    accept="image/*"
                    className="rounded-lg"
                  >
                    <div className="py-4">
                      <p className="text-3xl mb-2" style={{ lineHeight: 1 }}>
                        <CloudUploadOutlined style={{ color: '#0D9488' }} />
                      </p>
                      <p className="text-sm font-medium text-gray-700">点击或拖拽上传图片</p>
                      <p className="text-xs text-gray-400 mt-1">支持 JPG / PNG 格式</p>
                    </div>
                  </Dragger>
                  {filePreview && (
                    <div className="mt-3">
                      <div className="relative group">
                        <img
                          src={filePreview}
                          alt="uploaded preview"
                          className="w-full max-h-40 object-contain rounded-lg border border-gray-200 bg-white"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors rounded-lg" />
                      </div>
                      <div className="flex items-center justify-between mt-2 px-1">
                        <span className="text-xs text-gray-500 truncate max-w-[200px]">{file?.name}</span>
                        <Button size="small" type="link" onClick={handleReset} className="!text-xs">
                          清除
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>

                {/* Params Card */}
                <Card
                  size="small"
                  title={<><SettingOutlined style={{ marginRight: 6 }} /> 参数设置</>}
                  className="shadow-sm hover:shadow-md transition-shadow duration-200"
                  styles={{ body: { padding: '12px' } }}
                  extra={
                    <Button size="small" type="link" onClick={handleReset}>
                      重置
                    </Button>
                  }
                >
                  <Space direction="vertical" className="w-full" size={12}>
                    {/* Palette */}
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">色卡品牌</label>
                      <Select
                        value={palette}
                        onChange={setPalette}
                        className="w-full mt-1"
                        options={palettes.map((p) => ({ label: p.toUpperCase(), value: p }))}
                        size="middle"
                      />
                    </div>

                    {/* Grid Size */}
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">网格尺寸</label>
                      <div className="flex items-center gap-2 mt-1">
                        <InputNumber
                          value={width}
                          onChange={(v) => setWidth(v)}
                          min={10}
                          max={200}
                          className="flex-1"
                          size="middle"
                          addonBefore="宽"
                        />
                        <span className="text-gray-400">×</span>
                        <InputNumber
                          value={height}
                          onChange={(v) => setHeight(v)}
                          min={10}
                          max={200}
                          className="flex-1"
                          size="middle"
                          addonBefore="高"
                        />
                      </div>
                    </div>

                    {/* Max Colors */}
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">最大颜色数</label>
                      <InputNumber
                        value={maxColors}
                        onChange={(v) => setMaxColors(v)}
                        min={1}
                        max={100}
                        placeholder="不限制"
                        className="w-full mt-1"
                        size="middle"
                      />
                    </div>

                    {/* Sliders */}
                    <div>
                      <div className="flex justify-between">
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">亮度</label>
                        <span className="text-xs font-mono text-teal-600">{brightness.toFixed(1)}</span>
                      </div>
                      <Slider value={brightness} onChange={setBrightness} min={0.5} max={1.5} step={0.1} />
                    </div>
                    <div>
                      <div className="flex justify-between">
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">对比度</label>
                        <span className="text-xs font-mono text-teal-600">{contrast.toFixed(1)}</span>
                      </div>
                      <Slider value={contrast} onChange={setContrast} min={0.5} max={1.5} step={0.1} />
                    </div>

                    {/* Advanced toggle */}
                    <div>
                      <Button
                        type="link"
                        size="small"
                        className="!px-0"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                      >
                        {showAdvanced ? '收起高级选项' : '展开高级选项'}
                      </Button>
                    </div>

                    {showAdvanced && (
                      <>
                        <div>
                          <div className="flex justify-between">
                            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">饱和度</label>
                            <span className="text-xs font-mono text-teal-600">{saturation.toFixed(1)}</span>
                          </div>
                          <Slider value={saturation} onChange={setSaturation} min={0.5} max={1.5} step={0.1} />
                        </div>
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium text-gray-500">清理孤豆</label>
                          <Switch
                            checked={removeIsolated}
                            onChange={setRemoveIsolated}
                            size="small"
                          />
                        </div>
                      </>
                    )}

                    <Divider style={{ margin: '4px 0' }} />

                    <Button
                      type="primary"
                      size="large"
                      block
                      onClick={handleGenerate}
                      loading={loading}
                      icon={<PictureOutlined />}
                      style={{
                        background: 'linear-gradient(135deg, #0D9488, #14B8A6)',
                        borderColor: '#0D9488',
                        height: 44,
                        fontWeight: 600,
                        fontSize: 15,
                      }}
                    >
                      生成图纸
                    </Button>
                  </Space>
                </Card>
              </Space>
            </Col>

            {/* Right: Preview on top, then stats, swatches, BOM */}
            <Col xs={24} lg={17}>
              <Spin spinning={loading} tip="正在生成图纸..." size="large">
                {result ? (
                  <Space direction="vertical" className="w-full" size={12}>
                    {/* Preview Tabs - moved to top */}
                    <Card
                      size="small"
                      className="shadow-sm"
                      styles={{ body: { padding: 0 } }}
                    >
                      <Tabs
                        defaultActiveKey="pattern"
                        size="small"
                        tabBarStyle={{ padding: '0 12px', marginBottom: 0 }}
                        items={[
                          {
                            key: 'pattern',
                            label: <span><AppstoreOutlined /> 拼豆图纸</span>,
                            children: (
                              <div className="bg-white rounded-b-lg border border-t-0 border-gray-200 p-3 overflow-auto" style={{ maxHeight: '65vh' }}>
                                <PatternCanvas
                                  pattern={result.pattern}
                                  paletteUsed={result.palette_used}
                                  size={result.size}
                                />
                              </div>
                            ),
                          },
                          {
                            key: 'preview',
                            label: <span><PictureOutlined /> 效果预览</span>,
                            children: (
                              <div className="text-center bg-white rounded-b-lg border border-t-0 border-gray-200 p-3">
                                <img
                                  src={`data:image/png;base64,${result.preview_png}`}
                                  alt="pixelated preview"
                                  className="max-w-full rounded"
                                  style={{ imageRendering: 'pixelated' }}
                                />
                              </div>
                            ),
                          },
                          {
                            key: 'grid',
                            label: <span><FileTextOutlined /> 符号图纸</span>,
                            children: (
                              <div className="bg-white rounded-b-lg border border-t-0 border-gray-200 p-3 overflow-auto" style={{ maxHeight: '65vh' }}>
                                <img
                                  src={`data:image/png;base64,${result.grid_png}`}
                                  alt="grid pattern"
                                  className="max-w-full rounded"
                                />
                              </div>
                            ),
                          },
                        ]}
                      />
                    </Card>

                    {/* Stats - compact inline tags */}
                    <div className="flex items-center gap-3 text-xs text-gray-500 px-1">
                      <span>网格 <span className="font-mono font-medium text-gray-700">{result.size.width}×{result.size.height}</span></span>
                      <span className="text-gray-300">|</span>
                      <span>颜色 <span className="font-mono font-medium text-teal-600">{result.stats.unique_colors}</span></span>
                      <span className="text-gray-300">|</span>
                      <span>豆数 <span className="font-mono font-medium text-gray-700">{result.stats.total_beads.toLocaleString()}</span></span>
                      {result.stats.empty_cells > 0 && (
                        <>
                          <span className="text-gray-300">|</span>
                          <span>空格 <span className="font-mono font-medium text-gray-700">{result.stats.empty_cells}</span></span>
                        </>
                      )}
                    </div>

                    {/* Palette Used Swatches */}
                    <Card
                      size="small"
                      title={
                        <span className="text-xs font-medium">
                          <AppstoreOutlined style={{ marginRight: 4, fontSize: 12 }} />
                          使用颜色 ({result.palette_used.length})
                        </span>
                      }
                      className="shadow-sm"
                      styles={{ body: { padding: '6px 12px' } }}
                    >
                      <div className="flex flex-wrap gap-1">
                        {result.palette_used.map((entry) => (
                          <div
                            key={entry.code}
                            className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white border border-gray-100"
                            title={`${entry.code} ${entry.name} (${entry.count})`}
                          >
                            <div
                              className="w-3.5 h-3.5 rounded-sm border border-gray-200"
                              style={{ backgroundColor: entry.hex }}
                            />
                            <span className="text-[11px] font-mono text-gray-600">{entry.code}</span>
                            <span className="text-[11px] text-gray-400">×{entry.count}</span>
                          </div>
                        ))}
                      </div>
                    </Card>

                    {/* BOM - collapsible */}
                    <Collapse
                      defaultActiveKey={[]}
                      size="small"
                      className="shadow-sm"
                      style={{ background: '#fff', borderRadius: 8, overflow: 'hidden' }}
                      items={[
                        {
                          key: 'bom',
                          label: (
                            <span className="text-sm font-medium">
                              <FileTextOutlined style={{ marginRight: 6 }} />
                              BOM 清单
                              <Tag color="teal" className="ml-2">{result.palette_used.length} 色</Tag>
                            </span>
                          ),
                          children: (
                            <Table
                              columns={bomColumns}
                              dataSource={result.palette_used}
                              rowKey="code"
                              size="small"
                              pagination={false}
                              scroll={{ y: 200 }}
                            />
                          ),
                        },
                      ]}
                    />
                  </Space>
                ) : (
                  <div
                    className="bg-white rounded-2xl border-2 border-dashed flex flex-col items-center justify-center text-center p-12"
                    style={{
                      height: 500,
                      borderColor: '#CCFBF1',
                      background: 'linear-gradient(135deg, rgba(240,253,250,0.5), rgba(255,255,255,0.8))',
                    }}
                  >
                    <div
                      className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                      style={{ background: 'linear-gradient(135deg, #CCFBF1, #F0FDFA)' }}
                    >
                      <AppstoreOutlined style={{ fontSize: 28, color: '#0D9488' }} />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-700 mb-2">等待生成图纸</h3>
                    <p className="text-sm text-gray-400 max-w-xs">
                      上传图片并设置参数后，点击「生成图纸」按钮即可生成拼豆图纸预览
                    </p>
                    <div className="mt-6 flex gap-6 text-xs text-gray-400">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-sm bg-teal-200" />
                        <span>拖拽上传</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-sm bg-blue-200" />
                        <span>设置参数</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-sm bg-orange-200" />
                        <span>一键生成</span>
                      </div>
                    </div>
                  </div>
                )}
              </Spin>
            </Col>
          </Row>
        </div>
      </div>
    </ConfigProvider>
  )
}

export default App
