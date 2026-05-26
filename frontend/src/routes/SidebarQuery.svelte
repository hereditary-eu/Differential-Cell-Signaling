<script lang="ts">
	import {
		filteringQueryStr,
		sender,
		receiver,
		highlightedCycle,
		aesSettings,
		goResults
	} from '$lib/stores';
	import type { GoResults } from '$lib/types';
	import { base } from '$app/paths';
	const backend = import.meta.env.VITE_BACKEND_URL ?? base;
	// CYCLES
	let max_length = $state(12);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let result = $state<{ nCycles: number; truncated: boolean; cycles: any } | null>(null);
	let activeIdx = $state<number | null>(null);

	async function findCycles() {
		loading = true;
		error = null;
		result = null;
		activeIdx = null;
		try {
			const res = await fetch(
				`${backend}/api/cycles?${$filteringQueryStr}&max_cycle_length=${max_length}&max_cycles=500`
			);
			if (!res.ok) throw new Error(`Server error ${res.status}`);
			result = await res.json();
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			loading = false;
		}
	}
	function toggleCycle(cycle: any, idx: any) {
		if (activeIdx === idx) {
			//click on already active cycle clears the selection
			activeIdx = null;
			highlightedCycle.set(null);
			return;
		}
		activeIdx = idx;
		const nodeIds: Set<string> = new Set(cycle.nodes.map((n: { id: any }) => String(n.id)));
		const edgePairs: Set<string> = new Set(
			cycle.edges.flatMap((e: { source: any; target: any; type: string }) => {
				const pair = `${e.source}->${e.target}`;
				console.log(e.source);
				return e.type === 'LR' ? [pair, `${e.target}->${e.source}`] : [pair];
			})
		);
		aesSettings.update((settings) => ({ ...settings, groupNodes: false }));
		highlightedCycle.set({ nodeIds, edgePairs });
	}
	function clearHighlight() {
		activeIdx = null;
		highlightedCycle.set(null);
	}
	$effect(() => {
		$filteringQueryStr;
		clearHighlight();
		result = null;
	});

	//   GOEA
	let onGoResults = $state<(res: GoResults | null) => void>(() => {});

	let showGOEA = $state(false);
	let organism = $state<'mmusculus' | 'hsapiens'>('mmusculus');
	let sources = $state<string[]>(['GO:BP', 'KEGG', 'REAC']);
	let significanceMethod = $state<'g_SCS' | 'bonferroni' | 'fdr'>('g_SCS');
	let pvCutoff = $state(0.05);
	let useCustomBackground = $state(false);
	let lrDB = $state('LR_pairs_Lagger_2023_mouse');
	let tfDB = $state('collecTRI_mouse');
	let rtfDB = $state('TF_PPR_KEGG_mouse');
	let useLR = $state(true);
	let useTF = $state(true);
	let useRTF = $state(true);

	let splitSubunits = $state(false);
	let subunitsDelimiter = $state(',');

	let customBackgroundFile = $state<File | null>(null);
	let customGenes = $state<string[]>([]);

	let goLoading = $state(false);
	let goError = $state<string | null>(null);
	// let goResult = $state<GoTerm[]>([]);
	let goMeta = $state<{
		query_size: number;
		background_size: number | null;
		n_significant: number;
	} | null>(null);

	const ALL_SOURCES = ['GO:BP', 'GO:MF', 'GO:CC', 'KEGG', 'REAC', 'WP'];
	const LR_DB_OPTS = [
		'LR_pairs_Lagger_2023_mouse',
		'LR_pairs_Lagger_2023_human',
		'LR_pairs_ConnectomeDB_2020',
		'LR_pairs_Skelly_2018_mouse'
	];
	const TF_DB_OPTS = [
		'collecTRI_mouse',
		'collecTRI_human',
		'TF_TG_TTRUSTv2_mouse',
		'TF_TG_TTRUSTv2_human'
	];
	const RTF_DB_OPTS = ['TF_PPR_KEGG_human', 'TF_PPR_KEGG_mouse'];

	function toggleSource(src: string) {
		sources = sources.includes(src) ? sources.filter((s) => s !== src) : [...sources, src];
	}

	$effect(() => {
		if (organism === 'mmusculus') {
			lrDB = 'LR_pairs_Lagger_2023_mouse';
			tfDB = 'collecTRI_mouse';
			rtfDB = 'TF_PPR_KEGG_mouse';
		} else {
			lrDB = 'LR_pairs_Lagger_2023_human';
			tfDB = 'collecTRI_human';
			rtfDB = 'TF_PPR_KEGG_human';
		}
	});
	async function handleCustomBackgroundFile(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		customBackgroundFile = file;
		const text = await file.text();
		// Support both comma and newline separated genes
		customGenes = text
			.split(/[\n,]+/)
			.map((g) => g.trim())
			.filter(Boolean);
	}
	async function runEnrichment() {
		if (sources.length === 0) return;
		goLoading = true;
		goError = null;
		goResults.set(null);
		goMeta = null;
		onGoResults(null); // clear downstream
		try {
			const params = new URLSearchParams($filteringQueryStr);
			params.set('organism', organism);
			params.set('sources', sources.join(','));
			params.set('significance_method', significanceMethod);
			params.set('pv_cutoff', String(pvCutoff));
			params.set('split_complexes', String(splitSubunits));
			params.set('subunits_delimiter', subunitsDelimiter);
			params.set('LR_DB', lrDB);
			params.set('TF_DB', tfDB);
			params.set('RTF_DB', rtfDB);
			params.set('use_lr', String(useLR));
			params.set('use_tf', String(useTF));
			params.set('use_rtf', String(useRTF));

			if (useCustomBackground && customGenes.length > 0) {
				params.set('use_custom_universe', 'true');
				// Pass genes as repeated query params
				customGenes.forEach((g) => params.append('custom_universe', g));
			} else {
				params.set('use_custom_universe', 'false');
			}
			const res = await fetch(`${backend}/api/go_enrichment?${params.toString()}`);
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw new Error(body.detail ?? `Server error ${res.status}`);
			}
			const data: GoResults = await res.json();
			console.log('go res:', data.results);
			goResults.set(data);
			goMeta = {
				query_size: data.query_size,
				background_size: data.background_size,
				n_significant: data.n_significant
			};
			onGoResults(data);
		} catch (err: unknown) {
			goError = err instanceof Error ? err.message : String(err);
			onGoResults(null);
		} finally {
			goLoading = false;
		}
	}
	function downloadCSV() {
		if (!$goResults?.results?.length) return;
		const cols = [
			'source',
			'native',
			'name',
			'p_value',
			'gene_ratio',
			'term_size',
			'query_size',
			'intersection_size',
			'precision',
			'recall',
			'intersections'
		];
		const header = cols.join(',');
		const rows = ($goResults?.results ?? []).map((r) =>
			cols
				.map((c) => {
					const v = (r as any)[c];
					const s = Array.isArray(v) ? v.join(';') : String(v ?? '');
					return s.includes(',') ? `"${s}"` : s;
				})
				.join(',')
		);
		const blob = new Blob([header + '\n' + rows.join('\n')], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'go_enrichment_results.csv';
		a.click();
		URL.revokeObjectURL(url);
	}
	$effect(() => {
		// whenever filtering query changes, reset GOEA state
		$filteringQueryStr;
		showGOEA = false;
		goResults.set(null);
		goMeta = null;
		goError = null;
	});
</script>

<div class="controls">
	<div class="control-row">
		<label for="max-len">Max cycle length</label>
		<input id="max-len" type="number" min="3" max="20" bind:value={max_length} />
	</div>

	<button
		id="find-cycles-btn"
		type="button"
		class="btn btn-primary"
		onclick={findCycles}
		disabled={loading}
	>
		{#if loading}
			<span class="spinner" aria-hidden="true"></span> Searching…
		{:else}
			Find Cycles
		{/if}
	</button>
</div>

{#if error}
	<p class="msg error">{error}</p>
{:else if result}
	<div class="result-header">
		<span class="count">
			{result.nCycles} cycle{result.nCycles !== 1 ? 's' : ''} found in {$sender} - {$receiver} subgraph
		</span>
		{#if result.truncated}
			<span class="badge truncated">Results truncated</span>
		{/if}
		{#if activeIdx !== null}
			<button class="clear-btn" type="button" onclick={clearHighlight}>Clear highlight</button>
		{/if}
	</div>

	{#if result.nCycles === 0}
		<p class="msg muted">No cycles detected in the current network.</p>
	{:else}
		<ul class="cycle-list">
			{#each result.cycles as cycle, idx}
				{@const active = activeIdx === idx}
				<li>
					<div
						class="{active ? 'active' : ''}cycle-card"
						class:active
						role="button"
						tabindex="0"
						onclick={() => toggleCycle(cycle, idx)}
						onkeydown={(e) => e.key === 'Enter' && toggleCycle(cycle, idx)}
					>
						<div class="card-header">
							<span class="cycle-label">Cycle {idx + 1}</span>
							<span class="cycle-meta">{cycle.length} nodes</span>
						</div>
						<div class="flow">
							{#each cycle.nodes as node, ni}
								<div class="node-pill">
									<span class="node-id">{node.name}</span>
								</div>
								<div class="edge-badge-wrap">
									<div class="edge-arrow">to</div>
								</div>
							{/each}
							<div class="node-pill back-ref">
								<span class="node-id muted">{cycle.nodes[0].name}</span>
							</div>
						</div>
					</div>
					{#if active}
						{@const nodeMap = Object.fromEntries(
							cycle.nodes.map((n: { id: any }) => [String(n.id), n])
						)}
						<div class="cycle-details">
							<p><strong>Edges:</strong></p>
							<ul>
								{#each cycle.edges as e}
									{@const src = nodeMap[String(e.source)]}
									{@const tgt = nodeMap[String(e.target)]}
									<li>
										<!-- {console.log(e)} -->
										<!-- e.source and target do not have name, celltype and moltype information -->
										{src ? `${src['name']} (${src['celltype']}, ${src['moltype']})` : e.source}
										{e.type === 'LR' ? '<->' : '->'}
										{tgt ? `${tgt['name']} (${tgt['celltype']}, ${tgt['moltype']})` : e.target}
										({e.type})
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
{/if}

<hr style="width: 100%; border: 1px solid black;" />

<button
	id="GEA-btn"
	type="button"
	class="btn btn-primary"
	onclick={() => (showGOEA = !showGOEA)}
	style="width: 100%;"
>
	{showGOEA ? '▲' : '▼'} ORA Enrichment Analysis
</button>
{#if showGOEA}
	<section class="goea-section">
		<div class="ctrl-group">
			<label for="organism">Organism</label>
			<div id="organism" class="segmented">
				{#each [['mmusculus', 'Mouse'], ['hsapiens', 'Human']] as [val, label]}
					<button
						class:active={organism === val}
						onclick={() => (organism = val as 'mmusculus' | 'hsapiens')}
					>
						{label}
					</button>
				{/each}
			</div>
		</div>

		<div class="ctrl-group">
			<label for="sources">Sources</label>
			<div id="sources" class="chip-row">
				{#each ALL_SOURCES as src}
					<button
						class="chip"
						class:active={sources.includes(src)}
						onclick={() => toggleSource(src)}
					>
						{src}
					</button>
				{/each}
			</div>
		</div>
		<div class="ctrl-group">
			<label for="correction-method">Correction method</label>
			<select id="correction-method" bind:value={significanceMethod}>
				<option value="g_SCS">g:SCS (default)</option>
				<option value="bonferroni">Bonferroni</option>
				<option value="fdr">FDR (BH) </option>
			</select>
		</div>
		<div class="ctrl-group">
			<label for="pv-cutoff">(adjusted) p-value cutoff</label>
			<input id="pv-cutoff" type="number" min="0" max="1" step="0.01" bind:value={pvCutoff} />
		</div>
		<div class="ctrl-group">
			<label for="split-complexes">Split protein complexes</label>
			<div class="inline-row">
				<input type="checkbox" id="split-complexes" bind:checked={splitSubunits} />
				<label for="split-complexes" style="margin:0; font-weight:normal;">Split subunits</label>
				{#if splitSubunits}
					<input
						type="text"
						placeholder="delimiter"
						bind:value={subunitsDelimiter}
						style="width:4rem;"
					/>
				{/if}
			</div>
		</div>
		<!-- Gene universe background -->
		<div class="ctrl-group">
			<label for="gene-universe">Gene universe background</label>
			<div id="gene-universe" class="inline-row">
				<input type="checkbox" id="custom-bg" bind:checked={useCustomBackground} />
				<label for="custom-bg" style="margin:0; font-weight:normal;">Use custom background</label>
			</div>
			{#if !useCustomBackground}
				<div class="db-selects">
					<div class="db-row">
						<input type="checkbox" id="use-lr" bind:checked={useLR} />
						<label for="use-lr">LR DB</label>
						<select bind:value={lrDB} disabled={!useLR}>
							{#each LR_DB_OPTS as db}<option value={db}>{db}</option>{/each}
						</select>
					</div>
					<div class="db-row">
						<input type="checkbox" id="use-tf" bind:checked={useTF} />
						<label for="use-tf">TF DB</label>
						<select bind:value={tfDB} disabled={!useTF}>
							{#each TF_DB_OPTS as db}<option value={db}>{db}</option>{/each}
						</select>
					</div>
					<div class="db-row">
						<input type="checkbox" id="use-rtf" bind:checked={useRTF} />
						<label for="use-rtf">RTF DB</label>
						<select bind:value={rtfDB} disabled={!useRTF}>
							{#each RTF_DB_OPTS as db}<option value={db}>{db}</option>{/each}
						</select>
					</div>
				</div>
			{:else}
				<div class="custom-bg-upload">
					<label for="bg-file" class="upload-label">
						{customBackgroundFile
							? customBackgroundFile.name
							: 'Upload gene list (.txt or .csv, comma-separated)'}
					</label>
					<input
						id="bg-file"
						type="file"
						accept=".txt,.csv"
						onchange={handleCustomBackgroundFile}
					/>
					{#if customGenes.length > 0}
						<span class="gene-count">{customGenes.length} genes loaded</span>
					{/if}
				</div>
			{/if}
		</div>
		<button
			class="run-btn"
			onclick={runEnrichment}
			disabled={goLoading ||
				sources.length === 0 ||
				(useCustomBackground && customGenes.length === 0)}
		>
			{#if goLoading}<span class="spinner"></span> Running…{:else}▶ Run Enrichment{/if}
		</button>

		{#if goError}
			<div class="go-error">{goError}</div>
		{/if}

		{#if goMeta}
			<div class="go-meta-bar">
				<span><strong>{goMeta.n_significant}</strong> significant terms</span>
				<span>Query: <strong>{goMeta.query_size}</strong> genes</span>
				{#if goMeta.background_size}<span
						>Background: <strong>{goMeta.background_size}</strong></span
					>{/if}
				{#if ($goResults?.results?.length ?? 0) > 0}
					<button class="download-btn" onclick={downloadCSV}>⬇ Download CSV</button>
				{/if}
			</div>
		{/if}
	</section>
{/if}

<!-- tooltips -->
<!-- to perfomr GO enrichment analysis we advise to use as gene universe, i.e. the conisdered backgroound of detecttabel genes, 
 the unione of genes present in the LR DB and TF-TG DB used upstream for CCC and TF analyses -->
<!-- flexibility to implement  -->
<!-- TF-TG: provide collecTRI (mouse-human) / user-defined (file upload?)-->
<!-- LR: provide some options from scSeqComm / user-defined -->
<!-- user declare whether nodes need subunits splitting -->
<!-- method for FDR correction -->
<!-- for GO: select one or both BP, MF -->
<!-- method flexxibility: ORA? -->
<style>
	/* ── Cycles ── */
	.controls {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}
	.control-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		font-size: 0.8rem;
		color: var(--color-text-muted, #6b7280);
	}
	.control-row input {
		width: 4rem;
		padding: 0.15rem 0.35rem;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 0.8rem;
		background: var(--color-surface, #fff);
		color: var(--color-text, #111);
	}
	.result-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.5rem;
		font-size: 0.8rem;
	}
	.count {
		font-weight: 600;
		color: var(--color-text, #111);
	}
	.badge.truncated {
		padding: 1px 6px;
		border-radius: 999px;
		background: #fef3c7;
		color: #92400e;
		border: 1px solid #fcd34d;
		font-size: 0.7rem;
	}
	.clear-btn {
		margin-left: auto;
		font-size: 0.7rem;
		padding: 1px 6px;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		cursor: pointer;
		background: transparent;
		color: var(--color-text-muted, #6b7280);
	}
	.clear-btn:hover {
		background: var(--color-surface-hover, #f3f4f6);
	}
	.cycle-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-height: 55vh;
		overflow-y: auto;
		padding-right: 2px;
	}
	.cycle-card {
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 8px;
		padding: 0.5rem 0.6rem;
		background: var(--color-surface, #fafafa);
		cursor: pointer;
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
	}
	.cycle-card.active {
		border: 2px solid #000;
		box-shadow: 0 0 0 2px #bfdbfe;
	}
	.card-header {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 0.45rem;
	}
	.cycle-label {
		font-weight: 700;
		font-size: 0.75rem;
		color: var(--color-text, #111);
	}
	.cycle-meta {
		font-size: 0.7rem;
		color: var(--color-text-muted, #9ca3af);
	}
	.flow {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 2px;
		row-gap: 4px;
	}
	.node-pill {
		display: inline-flex;
		align-items: center;
		padding: 2px 7px;
		border-radius: 999px;
		border: 1px solid #d1d5db;
		background: #f3f4f6;
		font-size: 0.68rem;
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
		white-space: nowrap;
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		color: #374151;
	}
	.node-pill.back-ref {
		opacity: 0.5;
		font-style: italic;
	}
	.edge-badge-wrap {
		display: inline-flex;
		align-items: center;
		gap: 1px;
		font-size: 0.65rem;
	}
	.edge-arrow {
		color: #9ca3af;
		font-size: 0.8rem;
		line-height: 1;
	}
	.msg {
		font-size: 0.8rem;
		margin: 0.5rem 0;
	}
	.error {
		color: #dc2626;
	}
	.muted {
		color: var(--color-text-muted, #9ca3af);
	}
	.cycle-details {
		font-size: 0.75rem;
		padding: 0.4rem 0.6rem;
		background: #f9fafb;
		border-radius: 0 0 8px 8px;
	}
	.cycle-details ul {
		margin: 0.25rem 0 0 1rem;
		padding: 0;
	}
	.cycle-details li {
		margin-bottom: 0.2rem;
	}

	/* ── GOEA ── */
	hr {
		margin: 0.75rem 0;
		border: none;
		border-top: 1px solid var(--color-border, #e5e7eb);
	}

	.goea-section {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		margin-top: 0.5rem;
		font-size: 0.8rem;
	}
	.ctrl-group {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.ctrl-group > label {
		font-size: 0.72rem;
		font-weight: 600;
		color: var(--color-text-muted, #6b7280);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.segmented {
		display: flex;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 6px;
		overflow: hidden;
	}
	.segmented button {
		flex: 1;
		padding: 0.25rem 0.5rem;
		border: none;
		background: transparent;
		font-size: 0.78rem;
		cursor: pointer;
		color: var(--color-text, #374151);
		transition: background 0.12s;
	}
	.segmented button.active {
		background: #000;
		color: #fff;
	}
	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
	}
	.chip {
		padding: 2px 8px;
		border-radius: 999px;
		border: 1px solid #d1d5db;
		background: #f3f4f6;
		font-size: 0.72rem;
		cursor: pointer;
		color: #374151;
		transition:
			background 0.12s,
			border-color 0.12s;
	}
	.chip.active {
		background: #f3f4f6;
		border-color: #000;
		color: #000;
		font-weight: 600;
	}
	select {
		padding: 0.2rem 0.4rem;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 4px;
		font-size: 0.75rem;
		background: var(--color-surface, #fff);
		color: var(--color-text, #111);
		width: 100%;
	}
	select:disabled {
		opacity: 0.4;
	}
	.inline-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.db-selects {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		margin-top: 0.2rem;
	}
	.db-row {
		display: grid;
		grid-template-columns: 1.2rem 2.8rem 1fr;
		align-items: center;
		gap: 0.35rem;
	}
	.db-row label {
		font-size: 0.72rem;
		font-weight: 600;
		color: #6b7280;
	}
	.custom-bg-upload {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.upload-label {
		display: inline-block;
		padding: 0.3rem 0.6rem;
		border: 1px dashed #000;
		border-radius: 6px;
		background: #eff6ff;
		color: #1d4ed8;
		font-size: 0.75rem;
		cursor: pointer;
	}
	.upload-label:hover {
		background: #dbeafe;
	}
	input[type='file'] {
		display: none;
	}
	.gene-count {
		font-size: 0.72rem;
		color: #16a34a;
		font-weight: 600;
	}
	.run-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.4rem 1rem;
		background: #000;
		color: #fff;
		border: none;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s;
	}
	.run-btn:hover:not(:disabled) {
		background: #495057;
	}
	.run-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.go-error {
		font-size: 0.75rem;
		color: #dc2626;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
		padding: 0.4rem 0.6rem;
	}
	.go-meta-bar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.75rem;
		font-size: 0.75rem;
		padding: 0.4rem 0.6rem;
		background: #f0fdf4;
		border: 1px solid #bbf7d0;
		border-radius: 6px;
		color: #15803d;
	}
	.download-btn {
		margin-left: auto;
		padding: 2px 8px;
		border: 1px solid #16a34a;
		border-radius: 4px;
		background: transparent;
		color: #16a34a;
		font-size: 0.72rem;
		cursor: pointer;
		font-weight: 600;
	}
	.download-btn:hover {
		background: #dcfce7;
	}

	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
		vertical-align: middle;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
