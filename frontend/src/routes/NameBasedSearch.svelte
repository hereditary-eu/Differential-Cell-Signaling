<!-- <script lang="ts">
	import { onMount } from 'svelte';
	export let value: string | null = null;
	export let onChange: (val: string) => void = () => {};

	export let molecules: string[] = [];
	let filtered: string[] = [];
	let search = '';
	let open = false;
	let loading = false;
	let error: string | null = null;
	let container: HTMLDivElement;

	onMount(async () => {
		loading = true;
		try {
			const res = await fetch('/api/molecule_list');
			if (!res.ok) throw new Error();
			molecules = await res.json();
			filtered = molecules;
		} catch {
			error = 'Failed to load molecules';
		} finally {
			loading = false;
		}
	});
	$: filtered = molecules.filter((m) => m.toLowerCase().includes(search.toLowerCase()));
	function selectItem(item: string) {
		value = item;
		search = item;
		open = false;
		onChange(item);
	}
	// Close dropdown when clicking outside
	function handleClickOutside(e: MouseEvent) {
		if (!container?.contains(e.target as Node)) {
			open = false;
		}
	}
	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});
</script>

<div class="wrapper" bind:this={container}>
	<input
		type="text"
		placeholder="Select molecule..."
		bind:value={search}
		on:focus={() => (open = true)}
	/>

	{#if open}
		<div class="dropdown">
			{#if loading}
				<div class="item">Loading...</div>
			{:else if error}
				<div class="item">{error}</div>
			{:else if filtered.length === 0}
				<div class="item">No results</div>
			{:else}
				{#each filtered as molecule}
					<div class="item" on:click={() => selectItem(molecule)}>
						{molecule}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.wrapper {
		position: relative;
		width: 300px;
	}

	input {
		width: 100%;
		padding: 8px;
	}

	.dropdown {
		position: absolute;
		width: 100%;
		border: 1px solid #ccc;
		background: white;
		max-height: 200px;
		overflow-y: auto;
		z-index: 10;
	}

	.item {
		padding: 8px;
		cursor: pointer;
	}

	.item:hover {
		background: #eee;
	}
</style> -->
