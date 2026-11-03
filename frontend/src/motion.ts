import { useEffect, useState } from 'react'

function parseNumericValue(value: string): { target: number; formatted: string; suffix: string; decimals: number } | null {
  const match = value.match(/^(-?[\d,]+(?:\.\d+)?)(.*)$/)
  if (!match) return null
  const target = Number(match[1].replaceAll(',', ''))
  if (!Number.isFinite(target)) return null
  return {
    target,
    formatted: match[1],
    suffix: match[2],
    decimals: match[1].split('.')[1]?.length ?? 0,
  }
}

/** Count a real numeric value into view; leave labels and non-numeric values untouched. */
export function useCountUpValue(value: string, enabled = true, duration = 760): string {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [displayValue, setDisplayValue] = useState(() => {
    const numeric = parseNumericValue(value)
    if (!enabled || reducedMotion || !numeric) return value
    const zero = numeric.decimals ? `0.${'0'.repeat(numeric.decimals)}` : '0'
    return `${zero}${numeric.suffix}`
  })

  useEffect(() => {
    const numeric = parseNumericValue(value)
    if (!enabled || reducedMotion || !numeric) return

    const formatter = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: numeric.decimals,
      maximumFractionDigits: numeric.decimals,
    })
    const started = performance.now()
    let frame = 0
    const animate = (now: number) => {
      const progress = Math.min(1, (now - started) / duration)
      const eased = 1 - (1 - progress) ** 3
      setDisplayValue(progress === 1 ? value : `${formatter.format(numeric.target * eased)}${numeric.suffix}`)
      if (progress < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [duration, enabled, reducedMotion, value])

  return enabled && !reducedMotion && parseNumericValue(value) ? displayValue : value
}
