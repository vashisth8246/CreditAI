import { createElement } from 'react'
import type { KeyboardEvent } from 'react'
import { dataSourceLabel, type DataSource, type InventoryItem } from './analytics.ts'
import { datasetReadiness } from './assessment.ts'

function sourceForDataset(id: string): DataSource {
  if (id.startsWith('EXT')) return 'unavailable'
  if (/^DS01[0-3]$/.test(id)) return 'synthetic'
  return 'historical'
}

function sourceTag(source: DataSource) {
  return createElement('span', { className: `source-tag source-${source}` }, dataSourceLabel(source))
}

export function DatasetInventoryTable({ items, selectedId = null, onSelect = () => undefined, showDetailButton = false, onDetailClick = () => undefined }: {
  items: InventoryItem[]
  selectedId?: string | null
  onSelect?: (datasetId: string) => void
  showDetailButton?: boolean
  onDetailClick?: (datasetId: string) => void
}) {
  return createElement('tbody', null, ...items.map((item) => {
    const select = () => onSelect(item.dataset_id)
    const onKeyDown = (event: KeyboardEvent<HTMLTableRowElement>) => { if (event.key === 'Enter') select() }
    return createElement('tr', { key: item.dataset_id, className: selectedId === item.dataset_id ? 'selected-row' : '', onClick: select, onKeyDown, tabIndex: 0 },
      createElement('td', null, createElement('div', { className: 'dataset-cell' },
        createElement('span', { className: 'dataset-code' }, item.dataset_id),
        createElement('div', null, createElement('strong', null, item.dataset_name),
          createElement('small', null, item.local_status, ' ', sourceTag(sourceForDataset(item.dataset_id)))),
      )),
      createElement('td', null, typeof item.row_count === 'number' ? item.row_count.toLocaleString('en-US') : String(item.row_count ?? '—')),
      createElement('td', { className: 'target-cell' }, String(item.target_column ?? '—')),
      createElement('td', { className: 'access-cell' }, String(item.license_and_access ?? '—')),
      createElement('td', null, createElement('span', {
        className: `status-badge readiness-${datasetReadiness(item).toLowerCase().replaceAll(/[^a-z]+/g, '-')}`,
      }, createElement('i'), datasetReadiness(item))),
      showDetailButton && createElement('td', null, createElement('button', {
        className: 'text-link',
        onClick: (e: React.MouseEvent) => { e.stopPropagation(); onDetailClick(item.dataset_id) },
        'aria-label': `View details for ${item.dataset_name}`
      }, 'View details')),
    )
  }))
}
