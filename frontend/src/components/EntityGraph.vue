<template>
  <div class="graph-container" ref="containerRef">
    <svg ref="svgRef" class="graph-svg">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        
        <filter id="shadow">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.3"/>
        </filter>
        
        <linearGradient id="newsGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#7dd3fc;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#38bdf8;stop-opacity:1" />
        </linearGradient>
        
        <linearGradient id="companyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#a78bfa;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:1" />
        </linearGradient>
        
        <linearGradient id="personGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#fbbf24;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#f59e0b;stop-opacity:1" />
        </linearGradient>
        
        <linearGradient id="productGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#4ade80;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#22c55e;stop-opacity:1" />
        </linearGradient>
        
        <linearGradient id="technologyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#f87171;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#ef4444;stop-opacity:1" />
        </linearGradient>
        
        <!-- 箭头标记：为不同关系类型创建不同颜色的箭头 -->
        <marker id="arrow-belongs_to" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#f59e0b" />
        </marker>
        <marker id="arrow-subsidiary_of" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#f97316" />
        </marker>
        <marker id="arrow-owns" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#ef4444" />
        </marker>
        <marker id="arrow-develops" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#22c55e" />
        </marker>
        <marker id="arrow-partners_with" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#38bdf8" />
        </marker>
        <marker id="arrow-competes_with" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#e879f9" />
        </marker>
        <marker id="arrow-invests_in" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#f43f5e" />
        </marker>
        <marker id="arrow-uses" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#2dd4bf" />
        </marker>
        <marker id="arrow-located_in" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#60a5fa" />
        </marker>
        <marker id="arrow-reports_to" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#fbbf24" />
        </marker>
        <marker id="arrow-joins" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#10b981" />
        </marker>
        <marker id="arrow-moved_to" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#8b5cf6" />
        </marker>
        <marker id="arrow-resigned_from" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#ef4444" />
        </marker>
        <marker id="arrow-succeeds" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#06b6d4" />
        </marker>
        <marker id="arrow-leads" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="#f59e0b" />
        </marker>
        <marker id="arrow-indirect" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="rgba(148, 163, 184, 0.75)" />
        </marker>
        <marker id="arrow-related" markerWidth="14" markerHeight="10" refX="14" refY="5" orient="auto" markerUnits="userSpaceOnUse">
          <polygon points="0 0, 14 5, 0 10" fill="rgba(125, 211, 252, 0.85)" />
        </marker>
      </defs>
      
      <g class="edges-layer"></g>
      <g class="edge-labels-layer"></g>
      <g class="nodes-layer"></g>
    </svg>
    
    <div v-if="hoveredNode" class="tooltip" :style="tooltipStyle">
      <div class="tooltip-header">
        <span class="tooltip-type" :class="`type-${hoveredNode.type}`">
          {{ hoveredNode.type }}
        </span>
        <span class="tooltip-name">{{ hoveredNode.name }}</span>
      </div>
      <div v-if="hoveredNode.type !== 'News'" class="tooltip-hint">
        点击选择此实体
      </div>
    </div>
    
    <div v-if="selectedNodes.length > 0" class="selected-info">
      <div class="selected-count">
        已选择 {{ selectedNodes.length }} 个实体
      </div>
      <div class="selected-list">
        <span
          v-for="node in selectedNodes"
          :key="node.id"
          class="selected-tag"
          :class="`type-${node.type}`"
        >
          {{ node.name }}
          <button @click="removeSelectedNode(node.id)" class="remove-btn">×</button>
        </span>
      </div>
    </div>
    
    <ContextMenu
      :visible="contextMenuVisible"
      :x="contextMenuPosition.x"
      :y="contextMenuPosition.y"
      :items="contextMenuItems"
      @close="contextMenuVisible = false"
      @select="handleContextMenuSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as d3 from 'd3'
import ContextMenu from './ContextMenu.vue'

interface Node {
  id: string
  name: string
  type: string
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
  color?: string       // 后端提供的颜色
  size?: number        // 后端提供的节点大小
  importance?: number  // 重要性分数
}

interface Edge {
  source: string
  target: string
  type: string
  salience?: number
  strength?: number    // 关系强度 1-5
  width?: number       // 边宽度
  context?: string     // 关系上下文
  dashed?: boolean     // 虚线表示间接关系
  properties?: any
}

interface Props {
  nodes: Node[]
  edges: Edge[]
  modelValue?: Node[]
}

interface Emits {
  (e: 'update:modelValue', nodes: Node[]): void
  (e: 'node-click', node: Node): void
  (e: 'node-drag-start', node: Node): void
  (e: 'node-drag-end', node: Node): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => []
})

const emit = defineEmits<Emits>()

const containerRef = ref<HTMLElement>()
const svgRef = ref<SVGElement>()
const selectedNodes = ref<Node[]>([...props.modelValue])
const hoveredNode = ref<Node | null>(null)
const tooltipStyle = ref({})
const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuNode = ref<Node | null>(null)

let simulation: d3.Simulation<d3.SimulationNodeDatum, undefined> | null = null
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null

const getNodeSize = (node: Node) => {
  // 如果后端提供了 size，使用它
  if (node.size) {
    return node.size
  }
  // 否则使用类型的默认大小
  const sizes: Record<string, number> = {
    company: 40,
    person: 35,
    product: 35,
    technology: 35,
    other: 30
  }
  return sizes[node.type] || sizes.other
}

const hashString = (value: string) => {
  let hash = 0
  for (let i = 0; i < value.length; i++) {
    hash = (hash << 5) - hash + value.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

const getNodeColor = (node: Node) => {
  // 按实体名分配同类型内的不同色相，避免整图过于单调
  const palettes: Record<string, string[]> = {
    News: ['#7dd3fc', '#38bdf8', '#22d3ee', '#60a5fa'],
    company: ['#ff6b6b', '#f97316', '#ef4444', '#fb7185', '#f59e0b'],
    person: ['#14b8a6', '#2dd4bf', '#0ea5e9', '#06b6d4', '#22d3ee'],
    product: ['#a78bfa', '#8b5cf6', '#c084fc', '#d946ef', '#f472b6'],
    technology: ['#34d399', '#10b981', '#84cc16', '#22c55e', '#4ade80'],
    event: ['#fbbf24', '#f59e0b', '#eab308', '#facc15'],
    location: ['#60a5fa', '#3b82f6', '#2dd4bf', '#38bdf8'],
    other: ['#94a3b8', '#cbd5e1', '#64748b', '#a1a1aa']
  }
  const type = node.type || 'other'
  const palette = palettes[type] || palettes.other
  const idx = hashString(`${type}:${node.name || node.id}`) % palette.length
  return palette[idx]
}

const getNodeStrokeColor = (node: Node) => {
  const c = d3.color(getNodeColor(node))
  return c ? c.darker(0.8).formatHex() : '#0f172a'
}

const normalizeEdgeType = (type: string) => {
  const raw = (type || 'related').trim()
  const canonical = raw
    .replace(/\s+/g, '_')
    .replace(/-/g, '_')
    .replace(/[^a-zA-Z0-9_]/g, '')
    .toLowerCase()

  const aliasMap: Record<string, string> = {
    developed: 'develops',
    developed_by: 'develops',
    partnered_with: 'partners_with',
    invested_in: 'invests_in',
    led_by: 'leads',
    movedto: 'moved_to',
    belongsto: 'belongs_to',
    competes: 'competes_with'
  }

  return aliasMap[canonical] || canonical || 'related'
}

const getEdgeColor = (type: string) => {
  const relationColors: Record<string, string> = {
    belongs_to: '#f59e0b',
    subsidiary_of: '#f97316',
    owns: '#ef4444',
    develops: '#22c55e',
    partners_with: '#38bdf8',
    competes_with: '#e879f9',
    invests_in: '#f43f5e',
    uses: '#2dd4bf',
    located_in: '#60a5fa',
    reports_to: '#fbbf24',
    joins: '#10b981',
    moved_to: '#8b5cf6',
    resigned_from: '#ef4444',
    succeeds: '#06b6d4',
    leads: '#f59e0b',
    indirect: 'rgba(148, 163, 184, 0.75)',
    related: 'rgba(125, 211, 252, 0.85)'
  }
  const key = normalizeEdgeType(type)
  return relationColors[key] || relationColors.related
}

const getEdgeMarker = (type: string) => {
  const key = normalizeEdgeType(type)
  const supportedMarkers = new Set([
    'belongs_to', 'subsidiary_of', 'owns', 'develops', 'partners_with',
    'competes_with', 'invests_in', 'uses', 'located_in', 'reports_to',
    'joins', 'moved_to', 'resigned_from', 'succeeds', 'leads', 'indirect', 'related'
  ])
  return supportedMarkers.has(key) ? `url(#arrow-${key})` : 'url(#arrow-related)'
}

const initializeGraph = () => {
  if (!containerRef.value || !svgRef.value || props.nodes.length === 0) return
  
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  if (width === 0 || height === 0) return
  
  const svgSel = d3.select(svgRef.value as SVGSVGElement)
  svg = svgSel
  svgSel.selectAll('.nodes-layer > *').remove()
  svgSel.selectAll('.edges-layer > *').remove()
  
  const nodes: Node[] = props.nodes.map(n => ({ ...n }))
  const nodeIdSet = new Set(nodes.map(n => n.id))
  const edges: any[] = props.edges
    .filter(e => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
    .map(e => ({
    source: e.source,
    target: e.target,
    type: e.type,
    salience: e.salience,
    strength: e.strength,
    width: e.width,
    dashed: e.dashed
  }))
  
  // 添加边界约束力，防止节点飞出可见区域
  const boundingBox = () => {
    const padding = 60  // 边距
    for (const node of nodes as any[]) {
      node.x = Math.max(padding, Math.min(width - padding, node.x || 0))
      node.y = Math.max(padding, Math.min(height - padding, node.y || 0))
    }
  }
  
  simulation = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
    .force('link', d3.forceLink(edges)
      .id((d: any) => d.id)
      .distance(120)
      .strength(0.8)
    )
    .force('charge', d3.forceManyBody()
      .strength(-400)
      .distanceMin(60)
      .distanceMax(300)
    )
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(50))
    .force('x', d3.forceX(width / 2).strength(0.05))  // 轻微向中心拉力
    .force('y', d3.forceY(height / 2).strength(0.05))
  
  const edgesLayer = svgSel.select('.edges-layer')
  
  const edge = edgesLayer.selectAll('line')
    .data(edges)
    .enter()
    .append('line')
    .attr('class', (d: any) => `edge ${d.dashed ? 'indirect-edge' : ''}`)
    .attr('stroke', (d: any) => getEdgeColor(d.type))
    .attr('stroke-width', (d: any) => {
      // 优先使用 width，其次使用 strength 计算，否则使用 salience
      if (d.width) return d.width
      if (d.strength) return 1 + (d.strength - 1) * 0.5
      return (d.salience || 0.5) * 4 + 1
    })
    .attr('stroke-dasharray', (d: any) => d.dashed ? '5,5' : '0')  // 虚线样式
    .attr('stroke-opacity', (d: any) => d.dashed ? 0.5 : 0.85)
    .attr('marker-end', (d: any) => getEdgeMarker(d.type))
  
  const edgeLabelsLayer = svgSel.select('.edge-labels-layer')
  
  const edgeLabels = edgeLabelsLayer.selectAll('text')
    .data(edges.filter((e: any) => e.type !== 'MENTIONS'))
    .enter()
    .append('text')
    .attr('class', 'edge-label')
    .attr('font-size', '10px')
    .attr('fill', (d: any) => getEdgeColor(d.type))
    .attr('text-anchor', 'middle')
    .attr('dy', -5)
    .text((d: any) => formatRelationType(d.type))
    .style('pointer-events', 'none')
    .style('opacity', 0)
  
  const nodesLayer = svgSel.select('.nodes-layer')
  
  const nodeGroup = nodesLayer.selectAll('g.node')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .call(d3.drag<SVGGElement, Node>()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended) as any
    )
  
  nodeGroup.append('circle')
    .attr('r', (d: Node) => getNodeSize(d))
    .attr('fill', (d: Node) => {
      // 如果后端提供了颜色，直接使用；否则使用梯度
      return getNodeColor(d)
    })
    .attr('stroke', (d: Node) => getNodeStrokeColor(d))
    .attr('stroke-width', 3)
    .attr('filter', 'url(#shadow)')
    .style('cursor', 'pointer')
  
  nodeGroup.append('text')
    .attr('dy', 4)
    .attr('text-anchor', 'middle')
    .attr('fill', '#e2e8f0')
    .attr('font-size', '11px')
    .attr('font-weight', '600')
    .text((d: Node) => truncateText(d.name, 8))
    .style('pointer-events', 'none')
  
  nodeGroup
    .on('mouseover', function(event: MouseEvent, d: Node) {
      d3.select(this).select('circle')
        .transition()
        .duration(200)
        .attr('r', getNodeSize(d) + 5)
        .attr('filter', 'url(#glow)')
      
      hoveredNode.value = d
      
      const [x, y] = d3.pointer(event, containerRef.value)
      tooltipStyle.value = {
        left: `${x + 15}px`,
        top: `${y - 10}px`
      }
      
      edge.attr('stroke-opacity', (e: any) => {
        return (e.source.id === d.id || e.target.id === d.id) ? 1 : 0.2
      })
      
      edgeLabels.style('opacity', (e: any) => {
        return (e.source.id === d.id || e.target.id === d.id) ? 1 : 0
      })
    })
    .on('mousemove', function(event: MouseEvent) {
      const [x, y] = d3.pointer(event, containerRef.value)
      tooltipStyle.value = {
        left: `${x + 15}px`,
        top: `${y - 10}px`
      }
    })
    .on('mouseout', function(_event: MouseEvent, d: Node) {
      d3.select(this).select('circle')
        .transition()
        .duration(200)
        .attr('r', getNodeSize(d))
        .attr('filter', 'url(#shadow)')
      
      hoveredNode.value = null
      
      edge.attr('stroke-opacity', 0.6)
      
      edgeLabels.style('opacity', 0)
    })
    .on('click', function(event: MouseEvent, d: Node) {
      event.stopPropagation()
      if (d.type === 'News') return
      
      const index = selectedNodes.value.findIndex(n => n.id === d.id)
      if (index >= 0) {
        selectedNodes.value.splice(index, 1)
        d3.select(this).select('circle')
          .attr('stroke-width', 3)
      } else {
        selectedNodes.value.push(d)
        d3.select(this).select('circle')
          .attr('stroke-width', 5)
      }
      emit('update:modelValue', [...selectedNodes.value])
      emit('node-click', d)
    })
    .on('contextmenu', function(event: MouseEvent, d: Node) {
      event.preventDefault()
      event.stopPropagation()
      
      contextMenuNode.value = d
      contextMenuPosition.value = { x: event.clientX, y: event.clientY }
      contextMenuVisible.value = true
    })
  
  simulation.on('tick', () => {
    boundingBox()  // 每一帧都约束节点在容器内
    
    edge
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => {
        const sx = d.source.x || 0
        const sy = d.source.y || 0
        const tx = d.target.x || 0
        const ty = d.target.y || 0
        const dx = tx - sx
        const dy = ty - sy
        const length = Math.sqrt(dx * dx + dy * dy) || 1
        const targetRadius = getNodeSize(d.target as Node)
        const arrowPadding = 16
        const offset = Math.min(targetRadius + arrowPadding, length - 2)
        return tx - (dx / length) * offset
      })
      .attr('y2', (d: any) => {
        const sx = d.source.x || 0
        const sy = d.source.y || 0
        const tx = d.target.x || 0
        const ty = d.target.y || 0
        const dx = tx - sx
        const dy = ty - sy
        const length = Math.sqrt(dx * dx + dy * dy) || 1
        const targetRadius = getNodeSize(d.target as Node)
        const arrowPadding = 16
        const offset = Math.min(targetRadius + arrowPadding, length - 2)
        return ty - (dy / length) * offset
      })
    
    edgeLabels
      .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
      .attr('y', (d: any) => (d.source.y + d.target.y) / 2)
    
    nodeGroup.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
  })
  
  function dragstarted(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
    if (!event.active && simulation) simulation.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
    emit('node-drag-start', d)
  }
  
  function dragged(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
    const padding = 60
    d.fx = Math.max(padding, Math.min(width - padding, event.x))
    d.fy = Math.max(padding, Math.min(height - padding, event.y))
  }
  
  function dragended(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
    if (!event.active && simulation) simulation.alphaTarget(0)
    d.fx = null
    d.fy = null
    emit('node-drag-end', d)
  }
}

const truncateText = (text: string, maxLength: number) => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 1) + '...'
}

const formatRelationType = (type: string) => {
  const relationMap: Record<string, string> = {
    'develops': '研发',
    'competes_with': '竞争',
    'partners_with': '合作',
    'owns': '拥有',
    'invests_in': '投资',
    'uses': '使用',
    'located_in': '位于',
    'belongs_to': '隶属',
    'subsidiary_of': '子公司于',
    'reports_to': '汇报给',
    'joins': '加入',
    'moved_to': '转至',
    'leads': '负责',
    'resigned_from': '离职自',
    'succeeds': '接任',
    'related': '相关',
    'indirect': '间接关联',
    'DEVELOPED': '开发',
    'LED_BY': '领导',
    'EVOLVED_FROM': '演进',
    'USES_TECHNOLOGY': '使用技术',
    'IS_PRODUCT_TYPE': '产品类型',
    'SOLVES_PROBLEM': '解决问题',
    'ENABLES': '赋能',
    'POWERED_BY': '驱动',
    'INTEGRATED_WITH': '集成',
    'BELONGS_TO': '属于',
    'SPECIALIZES_IN': '专精',
    'FOCUSES_ON': '专注',
    'PARTNERED_WITH': '合作',
    'COMPETES_WITH': '竞争',
    'SUPPLIES_TO': '供应',
    'INVESTED_IN': '投资',
    'OWNS': '拥有',
    'USED_IN': '用于',
    'BELONGS_TO_CATEGORY': '属于类别'
  }
  return relationMap[type] || relationMap[(type || '').toLowerCase()] || type
}

const removeSelectedNode = (nodeId: string) => {
  const index = selectedNodes.value.findIndex(n => n.id === nodeId)
  if (index >= 0) {
    selectedNodes.value.splice(index, 1)
    emit('update:modelValue', [...selectedNodes.value])
    
    if (svg) {
      svg.selectAll('g.node')
        .filter((d: any) => d.id === nodeId)
        .select('circle')
        .attr('stroke-width', 3)
    }
  }
}

watch(() => props.nodes, () => {
  setTimeout(() => {
    initializeGraph()
  }, 100)
}, { deep: true })

watch(() => props.modelValue, (newVal) => {
  selectedNodes.value = [...newVal]
}, { deep: true })

const contextMenuItems = computed(() => {
  if (!contextMenuNode.value) return []
  
  const isSelected = selectedNodes.value.some(n => n.id === contextMenuNode.value!.id)
  
  return [
    {
      id: 'add-to-analysis',
      label: isSelected ? '已加入按图索骥' : '加入"按图索骥"',
      shortcut: '',
      disabled: isSelected,
      action: () => {
        if (!isSelected && contextMenuNode.value) {
          selectedNodes.value.push(contextMenuNode.value!)
          emit('update:modelValue', [...selectedNodes.value])
        }
      }
    },
    {
      id: 'view-details',
      label: '查看实体详情',
      shortcut: '',
      disabled: false,
      action: () => {
        if (contextMenuNode.value) {
          emit('node-click', contextMenuNode.value!)
        }
      }
    }
  ]
})

const handleContextMenuSelect = (item: any) => {
  if (item.action) {
    item.action()
  }
}

onMounted(() => {
  setTimeout(() => {
    initializeGraph()
  }, 200)
})

onUnmounted(() => {
  if (simulation) {
    simulation.stop()
  }
})
</script>

<style scoped>
.graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
  background: radial-gradient(circle at center, rgba(125, 211, 252, 0.05) 0%, transparent 70%),
              rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 1rem;
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
}

.node circle {
  transition: all 0.3s ease;
}

.node:hover circle {
  filter: url(#glow) !important;
}

.edge {
  transition: stroke-opacity 0.3s ease;
}

.edge-label {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  transition: opacity 0.3s ease;
}

.tooltip {
  position: absolute;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(125, 211, 252, 0.3);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  pointer-events: none;
  z-index: 1000;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 150px;
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.tooltip-type {
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.type-News {
  background: rgba(125, 211, 252, 0.2);
  color: #7dd3fc;
}

.type-company {
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
}

.type-person {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.type-product {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.type-technology {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.type-other {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}

.tooltip-name {
  color: #e2e8f0;
  font-weight: 600;
  font-size: 0.875rem;
}

.tooltip-hint {
  color: rgba(125, 211, 252, 0.7);
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.selected-info {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  right: 1rem;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(125, 211, 252, 0.3);
  border-radius: 0.75rem;
  padding: 1rem;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.selected-count {
  font-size: 0.875rem;
  color: #7dd3fc;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.selected-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid;
}

.selected-tag.type-company {
  background: rgba(167, 139, 250, 0.15);
  border-color: rgba(167, 139, 250, 0.4);
  color: #a78bfa;
}

.selected-tag.type-person {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
  color: #fbbf24;
}

.selected-tag.type-product {
  background: rgba(74, 222, 128, 0.15);
  border-color: rgba(74, 222, 128, 0.4);
  color: #4ade80;
}

.selected-tag.type-technology {
  background: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.4);
  color: #f87171;
}

.remove-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0;
  width: 1rem;
  height: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.remove-btn:hover {
  opacity: 1;
}
</style>
