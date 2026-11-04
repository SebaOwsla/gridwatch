import { demoMeasurementsFor } from './demo'
import { METRICS, type Measurement, type MetricKey, type MetricStatistics, type TrendBucket, type TrendResponse } from './types'

export function demoTrendFor(equipmentId: string, hours: 24 | 168): TrendResponse {
  const bucket_minutes = hours === 24 ? 5 : 60
  const bucketMs = bucket_minutes * 60_000
  const cutoff = Date.now() - hours * 3_600_000
  const rows = demoMeasurementsFor(equipmentId).filter((row) =>
    row.quality === 'valid' && Date.parse(row.measured_at) >= cutoff,
  )
  const grouped = new Map<number, Measurement[]>()
  for (const row of rows) {
    const start = Math.floor(Date.parse(row.measured_at) / bucketMs) * bucketMs
    grouped.set(start, [...(grouped.get(start) ?? []), row])
  }
  const valuesFor = (group: Measurement[], key: MetricKey) =>
    group.map((row) => row[key]).filter((value): value is number => value !== null)
  const average = (values: number[]) => values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length : null

  const buckets: TrendBucket[] = [...grouped.entries()].sort(([a], [b]) => a - b).map(([start, group]) => {
    const metrics = Object.fromEntries(METRICS.map(({ key }) => [key, average(valuesFor(group, key))])) as Pick<Measurement, MetricKey>
    return { bucket_start: new Date(start).toISOString(), sample_count: group.length, ...metrics }
  })
  const statistics = Object.fromEntries(METRICS.map(({ key }) => {
    const values = valuesFor(rows, key)
    const stats: MetricStatistics = {
      minimum: values.length ? Math.min(...values) : null,
      average: average(values),
      maximum: values.length ? Math.max(...values) : null,
    }
    return [key, stats]
  })) as Record<MetricKey, MetricStatistics>

  return { equipment_id: equipmentId, hours, bucket_minutes, valid_samples: rows.length, buckets, statistics }
}
