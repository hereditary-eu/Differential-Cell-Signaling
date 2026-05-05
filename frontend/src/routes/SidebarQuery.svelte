<script lang="ts">
	import { filteringQueryStr, sender, receiver, highlightedCycle } from '$lib/stores';

	const backend = import.meta.env.VITE_BACKEND_URL;

	let max_length = 12;
	let loading = false;
	let error: string | null = null;
	let result: { nCycles: number; truncated: boolean; cycles: any } | null = null;
	let activeIdx: number | null = null;

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
		if (activeIdx === idx) { //click on already active cycle clears the selection
			activeIdx = null;
			highlightedCycle.set(null);
			return;
		}
		activeIdx = idx;
		const nodeIds: Set<string> = new Set(cycle.nodes.map((n: { id: any }) => String(n.id)));
		const edgePairs: Set<string> = new Set(
			cycle.edges.flatMap((e: { source: any; target: any; type: string }) => {
				const pair = `${e.source}->${e.target}`;
				return e.type === 'LR' ? [pair, `${e.target}->${e.source}`] : [pair];
			})
		);
		highlightedCycle.set({ nodeIds, edgePairs });
  }
  function clearHighlight() {
	activeIdx = null;
    highlightedCycle.set(null);
  }
  $: {$filteringQueryStr; clearHighlight(); result = null; }
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
		on:click={findCycles}
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
      	<button class="clear-btn" type="button" on:click={clearHighlight}>Clear highlight</button>
    	{/if}
	</div>

	{#if result.nCycles === 0}
		<p class="msg muted">No cycles detected in the current network.</p>

	{:else}
		<!-- <p class="hint">Click a cycle to highlight it in the network.</p> -->
		<ul class="cycle-list">
			{#each result.cycles as cycle, idx}
				{@const active = activeIdx === idx}
				<li>
					<div
						class="cycle-card"
						class:active
						role="button"
						tabindex="0"
						on:click={() => toggleCycle(cycle, idx)}
						on:keydown={(e) => e.key === 'Enter' && toggleCycle(cycle, idx)}
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
			</li>
			{/each}
		</ul>
	{/if}
{/if}

<hr />

<button id="GEA-btn" type="button" class="btn btn-primary" disabled>
	Perform GO Enrichment Analysis
</button>

<style>
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
	.clear-btn:hover { background: var(--color-surface-hover, #f3f4f6); }

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
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
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
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
		vertical-align: middle;
		margin-right: 4px;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	hr {
		margin: 0.75rem 0;
		border: none;
		border-top: 1px solid var(--color-border, #e5e7eb);
	}
</style>
