<script lang="ts">
	import { highlightedNode, selectedNode, selectedNodeName, filteringQueryStr } from '$lib/stores';

	import { base } from '$app/paths';
	const backend = import.meta.env.VITE_BACKEND_URL ?? base;

	let query = $state('');
	let suggestions: { id: string; verbose_id: string; name: string; celltype: string }[] = $state(
		[]
	);
	let open = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout>; //avoid reacting continuously to user typing, a bit of patience :)

	async function fetchSuggestions(q: string) {
		if (q.length < 1) {
			suggestions = [];
			open = false;
			return;
		} // wait till having two letters
		try {
			// encodeURIcomponent escapes characters with UTF-8
			const res = await fetch(
				`${backend}/api/molecules_names_list?${$filteringQueryStr}&q=${encodeURIComponent(q)}`
			);
			const data = await res.json();
			suggestions = data.molecules ?? [];
			open = suggestions.length > 0;
		} catch {
			suggestions = [];
		}
	}
	function onInput() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => fetchSuggestions(query), 220); // 220ms to wait
		if (!query) {
			highlightedNode.set(null);
			open = false;
		}
	}
	function select(s: { id: string; verbose_id: string; name: string; celltype: string }) {
		query = s.name;
		open = false;
		highlightedNode.set(s.verbose_id);
		selectedNode.set(s.id);
		selectedNodeName.set(s.name);
		console.log('update selectedNode from SidebarSearch: ', $selectedNode, ' ', $selectedNodeName);
	}
	// Highlight ALL nodes sharing this name across celltypes
	function selectAllCelltypes(name: string) {
		query = name;
		open = false;
		highlightedNode.set(`name:${name}`); // special prefix to signal "match by name"
	}
	// Group suggestions by name for display
	let groupedByName = $derived(
		suggestions.reduce(
			(acc, s) => {
				if (!acc[s.name]) acc[s.name] = [];
				acc[s.name].push(s);
				return acc;
			},
			{} as Record<string, typeof suggestions>
		)
	);
	function clear() {
		query = '';
		open = false;
		highlightedNode.set(null);
	}
	function highlight(text: string, q: string): string {
		//there seems also to be Highlight that can be imported from Svelte
		if (!q) return text;
		const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		return text.replace(new RegExp(`(${escaped})`, 'gi'), '<span class="match">$1</span>');
	}
</script>

<div class="search-wrap">
	<div class="input-row">
		<input
			class="form-control form-control-sm"
			type="text"
			placeholder="Search molecule name..."
			bind:value={query}
			oninput={onInput}
			onblur={() => setTimeout(() => (open = false), 150)}
			onfocus={() => suggestions.length && (open = true)}
		/>
		{#if query}
			<button class="clear-btn" onclick={clear} aria-label="Clear">x</button>
		{/if}
	</div>

	{#if open}
		<ul class="suggestions">
			{#each Object.entries(groupedByName) as [name, entries]}
				{#if entries.length > 1}
					<li class="group-header">
						<button class="all-btn" onmousedown={() => selectAllCelltypes(name)}>
							{@html highlight(name, query)}
							<span class="badge">all · {entries.length} cell types</span>
						</button>
					</li>
				{/if}
				{#each entries as s}
					<li class="entry" class:indent={entries.length > 1}>
						<button onmousedown={() => select(s)}>
							{#if entries.length === 1}
								{@html highlight(s.name, query)}
							{/if}
							<span class="ct-tag">{s.celltype}</span>
						</button>
					</li>
				{/each}
			{/each}
		</ul>
	{/if}

	{#if $highlightedNode}
		<p class="hint">
			Highlighting: <strong>
				{$highlightedNode.startsWith('name:')
					? $highlightedNode.slice(5) + ' (all cell types)'
					: $highlightedNode}
			</strong>
		</p>
	{/if}
</div>

<style>
	.search-wrap {
		position: relative;
	}
	.input-row {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	input {
		flex: 1;
	}
	.clear-btn {
		border: none;
		background: none;
		cursor: pointer;
		color: #888;
		font-size: 0.8rem;
		padding: 2px 4px;
	}
	.clear-btn:hover {
		color: #333;
	}
	.suggestions {
		position: absolute;
		z-index: 999;
		top: 100%;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 4px;
		max-height: 220px;
		overflow-y: auto;
		margin: 2px 0 0;
		padding: 0;
		list-style: none;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}
	.suggestions li button {
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		padding: 5px 10px;
		cursor: pointer;
		font-size: 0.82rem;
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.suggestions li button:hover {
		background: #f0f4ff;
	}
	.group-header button {
		font-weight: 600;
		color: #333;
	}
	.entry.indent button {
		padding-left: 20px;
		color: #555;
	}
	.ct-tag {
		font-size: 0.72rem;
		background: #e9ecef;
		border-radius: 3px;
		padding: 1px 5px;
		color: #495057;
		margin-left: auto;
	}
	.badge {
		font-size: 0.68rem;
		background: #0d6efd22;
		color: #0d6efd;
		border-radius: 3px;
		padding: 1px 5px;
		margin-left: auto;
	}
	:global(.match) {
		font-weight: 700;
		color: #0d6efd;
	}
	.hint {
		margin: 6px 0 0;
		font-size: 0.75rem;
		color: #555;
	}
</style>
