<script lang="ts">
	import { goResults } from '$lib/stores';
	import type { GoTerm } from '$lib/types';
	// import * as d3 from 'd3';
    
	let sigTerms = $derived($goResults ? $goResults.results.filter((r) => r.significant) : []); //actually useless, already filtered

	// Top N for bubble chart
	const TOP_N = 25;
	let topTerms = $derived(
		[...sigTerms].sort((a, b) => a.p_value - b.p_value).slice(0, TOP_N)
	);

	// Source counts (significant)
	let sourceCounts = $derived(() => {
		const counts: Record<string, number> = {};
		for (const t of sigTerms) counts[t.source] = (counts[t.source] ?? 0) + 1;
		return Object.entries(counts).sort((a, b) => b[1] - a[1]);
	});

	// Table state
	type SortKey = keyof GoTerm;
	let sortKey = $state<SortKey>('p_value');
	let sortAsc = $state(true);
	let filterSource = $state('ALL');
	let filterText = $state('');
	let expandedRow = $state<string | null>(null);

	let allSources = $derived(['ALL', ...new Set($goResults?.results.map((r) => r.source) ?? [])]);

	let filteredRows = $derived(() => {
		if (!$goResults) return [];
		let rows = $goResults.results;
		if (filterSource !== 'ALL') rows = rows.filter((r) => r.source === filterSource);
		if (filterText.trim()) {
			const q = filterText.trim().toLowerCase();
			rows = rows.filter((r) => r.name.toLowerCase().includes(q) || r.native.toLowerCase().includes(q));
		}
		return [...rows].sort((a, b) => {
			const av = (a as any)[sortKey];
			const bv = (b as any)[sortKey];
			if (av == null) return 1;
			if (bv == null) return -1;
			return sortAsc ? (av < bv ? -1 : 1) : av > bv ? -1 : 1;
		});
	});

	function toggleSort(key: SortKey) {
		if (sortKey === key) sortAsc = !sortAsc;
		else { sortKey = key; sortAsc = true; }
	}

	// Bubble chart 
	// let svgEl: SVGSVGElement;
	// let tooltip: | { x: number; y: number; term: GoTerm } | null = null;
	const MARGIN = { top: 16, right: 140, bottom: 48, left: 220 };
	let chartContainerWidth = $state(0);
	const CHART_W = $derived(Math.max(300, (chartContainerWidth - 32) ));
	const CHART_H_PER_ROW = 22;

	let chartH = $derived(Math.max(200, topTerms.length * CHART_H_PER_ROW + MARGIN.top + MARGIN.bottom));
	let innerW = $derived(CHART_W - MARGIN.left - MARGIN.right);
	let innerH = $derived(chartH - MARGIN.top - MARGIN.bottom);

	// x scale: gene_ratio [0 … max]
	let maxGR = $derived(Math.max(...topTerms.map((t) => t.gene_ratio ?? 0), 0.01));
	function xScale(v: number) { return (v / maxGR) * innerW; }

	// y scale: ordinal by index
	function yScale(i: number) { return (i / Math.max(topTerms.length - 1, 1)) * innerH; }

	// size scale: intersection_size 
	let maxIS = $derived(Math.max(...topTerms.map((t) => t.intersection_size), 1));
	function rScale(v: number) { return 1 + (v / maxIS) * 10; }

	// colour scale: -log10(p) → blue gradient
	let maxLogP = $derived(Math.max(...topTerms.map((t) => -Math.log10(t.p_value)), 1));
	function colourScale(p: number): string {
		const t = Math.min(-Math.log10(p) / maxLogP, 1);
		// interpolate #bfdbfe → #1d4ed8
		const r = Math.round(191 + t * (29 - 191));
		const g = Math.round(219 + t * (78 - 219));
		const b = Math.round(254 + t * (216 - 254));
		return `rgb(${r},${g},${b})`;
	}

	// x axis ticks
	let xTicks = $derived(
		Array.from({ length: 5 }, (_, i) => +((maxGR * i) / 4).toFixed(3))
	);

	// Source bar chart
	const BAR_H = 22;
	let BAR_MAX_W = $derived(CHART_W / 3);
	let maxSourceCount = $derived(Math.max(...sourceCounts().map((e) => e[1]), 1));

	// Source colour map
	const SOURCE_COLOURS: Record<string, string> = {
		'GO:BP': '#86efac',
		'GO:MF': '#93c5fd',
		'GO:CC': '#fca5a5',
		'KEGG':  '#fcd34d',
		'REAC':  '#c4b5fd',
		'WP':    '#6ee7b7'
	};
	function srcColour(src: string) { return SOURCE_COLOURS[src] ?? '#cbd5e1'; }

	let tooltip = $state<{ x: number; y: number; term: GoTerm } | null>(null);
</script>

{#if !$goResults || $goResults.results.length === 0}
	<div class="empty-state">
		<p>Run Enrichment Analysis to see results here.</p>
	</div>
{:else}
	<div class="goea-results">
		<div class="results-header">
			<div class="header-stats">
				<span class="stat-pill sig">{$goResults.n_significant} significant terms</span>
				<span class="stat-pill">Query: {$goResults.query_size} genes</span>
				{#if $goResults.background_size}<span class="stat-pill">Background: {$goResults.background_size}</span>{/if}
			</div>
			<!-- <button class="dl-btn" onclick={downloadCSV}>⬇ Download filtered CSV</button> -->
		</div>

		<div class="charts-row">
			<div class="chart-card bubble-card" bind:clientWidth={chartContainerWidth}>
				<h4 class="chart-title">Top {Math.min(TOP_N, topTerms.length)} significant terms — Gene ratio bubble plot</h4>
				{#if topTerms.length === 0}
					<p class="no-sig">No significant terms to display.</p>
				{:else}
					<div class="bubble-scroll">
						<svg
							viewBox="0 0 {CHART_W} {chartH}"
							width="100%"
							height={chartH}
							role="img"
							aria-label="Bubble chart of enriched terms"
						>
							<g transform="translate({MARGIN.left},{MARGIN.top})">
								<!-- Grid lines -->
								{#each xTicks as tick}
									<line
										x1={xScale(tick)} y1="0"
										x2={xScale(tick)} y2={innerH}
										stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4 3"
									/>
								{/each}

								<!-- Bubbles -->
								{#each topTerms as term, i}
									{@const cx = xScale(term.gene_ratio ?? 0)}
									{@const cy = yScale(i)}
									{@const r = rScale(term.intersection_size)}
									<circle
										{cx} {cy} {r}
										fill={colourScale(term.p_value)}
										stroke="#94a3b8"
										stroke-width="0.8"
										opacity="0.9"
										role="button"
										tabindex="0"
										aria-label="{term.name}, p={term.p_value.toExponential(2)}"
										style="cursor:pointer"
										onmouseenter={(e) => { tooltip = { x: cx + MARGIN.left + r + 4, y: cy + MARGIN.top, term }; }}
										onmouseleave={() => { tooltip = null; }}
									/>
									<!-- Y-axis label -->
									<text
										x="-8" y={cy}
										text-anchor="end"
										dominant-baseline="middle"
										font-size="10"
										fill="#374151"
										style="font-family: 'JetBrains Mono', monospace;"
									>
										{term.name.length > 30 ? term.name.slice(0, 28) + '…' : term.name}
									</text>
									<!-- source badge -->
									<text
										x={innerW + 20} y={cy}
										dominant-baseline="middle"
										font-size="9"
										fill={srcColour(term.source)}
										font-weight="700"
									>{term.source}</text>
								{/each}

								<!-- X axis -->
								<line x1="0" y1={innerH + 8} x2={innerW} y2={innerH + 8} stroke="#9ca3af" stroke-width="1" />
								{#each xTicks as tick}
									<text x={xScale(tick)} y={innerH + 22} text-anchor="middle" font-size="9" fill="#6b7280">{tick}</text>
								{/each}
								<text x={innerW / 2} y={innerH + 38} text-anchor="middle" font-size="10" fill="#6b7280">Gene ratio</text>

								<!-- Legend: size -->
								{#each [1, Math.round(maxIS / 2), maxIS] as sv, si}
									{@const lx = innerW + 100}
									{@const ly = 20 + si * 30}
									<circle cx={lx} cy={ly} r={rScale(sv)} fill="#cbd5e1" stroke="#94a3b8" stroke-width="0.8" />
									<text x={lx + 24} y={ly} dominant-baseline="middle" font-size="9" fill="#374151">{sv}</text>
								{/each}
								<text x={innerW + 80} y={8} font-size="9" fill="#6b7280" font-weight="600">Count</text>
							</g>
						</svg>
					</div>

					<!-- Tooltip  -->
					 <!-- still not shown properly if gets outside of container, also tried Z 9999 -->
					{#if tooltip}
						<div
							class="bubble-tooltip"
							style="left: {tooltip.x}px; top: {tooltip.y}px;"
						>
							<strong>{tooltip.term.name}</strong><br />
							<span class="tip-row">ID: {tooltip.term.native}</span><br />
							<span class="tip-row">p = {tooltip.term.p_value.toExponential(3)}</span><br />
							<span class="tip-row">Gene ratio: {tooltip.term.gene_ratio?.toFixed(3)}</span><br />
							<span class="tip-row">Intersection: {tooltip.term.intersection_size} / {tooltip.term.term_size}</span><br />
							{#if tooltip.term.intersections?.length}
								<span class="tip-row genes">{tooltip.term.intersections.slice(0, 8).join(', ')}{tooltip.term.intersections.length > 8 ? '…' : ''}</span>
							{/if}
						</div>
					{/if}
				{/if}
			</div>

			<div class="chart-card source-card">
				<h4 class="chart-title">Terms by source</h4>
				{#if sourceCounts().length === 0}
					<p class="no-sig">No significant terms.</p>
				{:else}
					<svg
						viewBox="0 0 {BAR_MAX_W + 100} {sourceCounts().length * BAR_H + 20}"
						width={BAR_MAX_W + 50}
						height={sourceCounts().length * BAR_H + 20}
						role="img"
					>
						{#each sourceCounts() as [src, cnt], i}
							{@const bw = (cnt / maxSourceCount) * BAR_MAX_W}
							<rect
								x="60" y={i * BAR_H + 4}
								width={bw} height={BAR_H - 6}
								fill={srcColour(src)}
								rx="3"
							/>
							<text x="56" y={i * BAR_H + BAR_H / 2} text-anchor="end" dominant-baseline="middle" font-size="11" fill="#374151" font-weight="600">{src}</text>
							<text x={60 + bw + 5} y={i * BAR_H + BAR_H / 2} dominant-baseline="middle" font-size="10" fill="#374151">{cnt}</text>
						{/each}
					</svg>
				{/if}
			</div>
		</div>

		<!-- Table  -->
		<div class="table-card">
			<div class="table-controls">
				<div class="filter-row">
					<input
						class="text-filter"
						type="search"
						placeholder="Search term name or ID…"
						bind:value={filterText}
					/>
					<div class="segmented-sm">
						{#each allSources as src}
							<button
								class:active={filterSource === src}
								onclick={() => (filterSource = src)}
								style={filterSource === src && src !== 'ALL' ? `background:${srcColour(src)};` : ''}
							>{src}</button>
						{/each}
					</div>
				</div>
				<span class="row-count">{filteredRows().length} terms</span>
			</div>

			<div class="table-scroll">
				<table>
					<thead>
						<tr>
							{#each [
								['source', 'Source'],
								['native', 'ID'],
								['name', 'Term'],
								['p_value', 'p-value'],
								['gene_ratio', 'Gene ratio'],
								['intersection_size', '#genes'],
								['term_size', 'Term size'],
								['precision', 'Precision'],
								['recall', 'Recall'],
							] as [key, label]}
								<th onclick={() => toggleSort(key as SortKey)} class:sorted={sortKey === key}>
									{label}
									{#if sortKey === key}<span class="sort-arrow">{sortAsc ? '↑' : '↓'}</span>{/if}
								</th>
							{/each}
							<th>Genes</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredRows() as row}
							<tr
								class:sig={row.significant}
								onclick={() => (expandedRow = expandedRow === row.native ? null : row.native)}
								style="cursor:pointer; background: {expandedRow === row.native ? '#f1f5f9' : 'transparent'}"
							>
								<td><span class="src-badge" style="background:{srcColour(row.source)}">{row.source}</span></td>
								<td class="mono">{row.native}</td>
								<td class="term-name">{row.name}</td>
								<td class="mono">{row.p_value.toExponential(2)}</td>
								<td class="mono">{row.gene_ratio?.toFixed(3) ?? '—'}</td>
								<td class="mono">{row.intersection_size}</td>
								<td class="mono">{row.term_size}</td>
								<td class="mono">{row.precision.toFixed(3)}</td>
								<td class="mono">{row.recall.toFixed(3)}</td>
								<td class="genes-cell">
									{#if expandedRow === row.native}
										{row.intersections?.join(', ') ?? '—'}
									{:else}
										{row.intersections?.slice(0, 3).join(', ')}{(row.intersections?.length ?? 0) > 3 ? ` +${row.intersections.length - 3}` : ''}
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>
{/if}

<style>
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 3rem 1rem;
		color: #9ca3af;
		font-size: 0.9rem;
	}

	.goea-results {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: 0.75rem;
		font-size: 0.8rem;
	}

	.results-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.header-stats { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	.stat-pill {
		padding: 2px 10px;
		border-radius: 999px;
		background: #f1f5f9;
		border: 1px solid #e2e8f0;
		color: #475569;
		font-size: 0.75rem;
	}
	/* .stat-pill.sig { 
		background: #f1f5f9; 
		border-color: #e2e8f0; 
		color: #475569; 
		font-weight: 700; 
	} */
	/* .dl-btn {
		padding: 4px 12px;
		border: 1px solid #3b82f6;
		border-radius: 6px;
		background: transparent;
		color: #3b82f6;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
	}
	.dl-btn:hover { background: #eff6ff; } */

	.charts-row {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		align-items: flex-start;
	}
	.chart-card {
		border: 1px solid #e2e8f0;
		border-radius: 10px;
		padding: 0.75rem 1rem;
		background: #fafafa;
	}
	.bubble-card { flex: 1 1 520px; position: relative; overflow: hidden; }
	.source-card { flex: 0 0 auto; }
	.chart-title {
		margin: 0 0 0.5rem;
		font-size: 0.78rem;
		font-weight: 700;
		color: #374151;
		letter-spacing: 0.01em;
	}
	.bubble-scroll { overflow-x: auto; }
	.no-sig { color: #9ca3af; font-size: 0.78rem; }
	/* keep it coherent with case study tooltips */
	.bubble-tooltip {
		position: absolute;
		pointer-events: none;
		background: #333;
		color: white;
		border-radius: 6px;
		padding: 6px 10px;
		font-size: 0.72rem;
		line-height: 1.6;
		max-width: 260px;
		z-index: 10;
	}
	.tip-row { color: #94a3b8; }
	.tip-row.genes { color: #7dd3fc; font-family: monospace; }

	.table-card {
		border: 1px solid #e2e8f0;
		border-radius: 10px;
		overflow: hidden;
		background: #fff;
	}
	.table-controls {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.75rem;
		gap: 0.5rem;
		border-bottom: 1px solid #e2e8f0;
		background: #f8fafc;
		flex-wrap: wrap;
	}
	.filter-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
	.text-filter {
		padding: 0.25rem 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.75rem;
		width: 200px;
	}
	.segmented-sm {
		display: flex;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		overflow: hidden;
	}
	.segmented-sm button {
		padding: 2px 8px;
		border: none;
		background: transparent;
		font-size: 0.7rem;
		cursor: pointer;
		color: #374151;
		transition: background 0.1s;
		border-right: 1px solid #d1d5db;
	}
	.segmented-sm button:last-child { border-right: none; }
	.segmented-sm button.active { background: #3b82f6; color: #fff; }
	.row-count { font-size: 0.72rem; color: #9ca3af; white-space: nowrap; }

	.table-scroll { overflow-x: auto; max-height: 380px; overflow-y: auto; }
	table { width: 100%; border-collapse: collapse; font-size: 0.75rem; }
	thead { position: sticky; top: 0; z-index: 2; background: #f1f5f9; }
	th {
		padding: 0.4rem 0.6rem;
		text-align: left;
		font-weight: 700;
		color: #475569;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		cursor: pointer;
		white-space: nowrap;
		border-bottom: 2px solid #e2e8f0;
		user-select: none;
	}
	th:hover { background: #e2e8f0; }
	th.sorted { color: #242b34; }
	.sort-arrow { margin-left: 2px; }
	td {
		padding: 0.35rem 0.6rem;
		border-bottom: 1px solid #f1f5f9;
		vertical-align: top;
		color: #374151;
	}
	tr:hover td { background: #f1f5f9; }
	tr.sig td { background: #ffffff; }
	tr.sig:hover td { background: #f1f5f9; }

	.src-badge {
		display: inline-block;
		padding: 1px 6px;
		border-radius: 4px;
		font-size: 0.68rem;
		font-weight: 700;
		color: #1e293b;
	}
	.mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.72rem; }
	.term-name { max-width: 260px; }
	.genes-cell { max-width: 200px; color: #475569; font-size: 0.7rem; word-break: break-word; }
</style>