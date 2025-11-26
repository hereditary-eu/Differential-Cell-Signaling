<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';

	// export let onFilter: (payload: { url: string }) => void = () => {};

	const backend = import.meta.env.VITE_BACKEND_URL;
	// Create an event dispatcher to emit the 'filter' event with the filter URL payload
	const dispatch = createEventDispatcher<{ filter: { url: string } }>();

	// State variables
	let foundCelltypes: string[] = [];
	let sender: string = '';
	let receiver: string = '';
	let reverseSig: boolean = false;
	let filterIntrascore = false;
	let filterInter = false;
	let filterPv = true;
	let pvThresh: number = 0.05;
	let minIntrascore = 0.5;
	let maxIntrascore = 1.0;
	let interDir: 'up' | 'down' = 'up';
	let filtersApplied = false;

	onMount(async () => {
		try {
			const res = await fetch(`${backend}/api/static_info`);
			const data = await res.json();
			foundCelltypes = data.celltypes;
		} catch (err) {
			console.error('Error fetching celltypes:', err);
		}
	});
	function applyFilters() {
		console.log(sender, receiver);
		const query = new URLSearchParams({
			sender: sender.toString(),
			receiver: receiver.toString(),
			reverse_sig: reverseSig.toString(),
			filter_intrascore: filterIntrascore.toString(),
			filter_pv: filterPv.toString(),
			filter_inter: filterInter.toString(),
			min_intrascore: minIntrascore.toString(),
			max_intrascore: maxIntrascore.toString(),
			pv_thresh: pvThresh.toString(),
			inter_dir: interDir
		});
		filtersApplied = true;
		dispatch('filter', { url: `${backend}/api/filtered_data?${query.toString()}` });
	}
</script>

<div style="margin-left: 3%;">
	<!-- Sidebar for filters -->
	<br />
	<h2>Filters Setting</h2>
	<br />
	<!--  cell type(s) selection -->
	<div>
		<p class="block mb-1 font-semibold">Select cell types:</p>
		<div class="d-flex">
			<div style="width: 45%;">
				<label for="sender-select">Sender:</label>
				<select
					id="sender-select"
					bind:value={sender}
					class="border rounded p-2"
					style="width: 100%;"
				>
					{#each foundCelltypes as ct}
						<option value={ct}>{ct}</option>
					{/each}
				</select>
			</div>

			<div style="width: 45%;">
				<label for="receiver-select">Receiver:</label>
				<select
					id="receiver-select"
					bind:value={receiver}
					class="border rounded p-2"
					style="width: 100%;"
				>
					{#each foundCelltypes as ct}
						<option value={ct}>{ct}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>
	<!-- Include also reverse signaling -->
	<div class="flex items-center gap-2">
		{#if sender === '' || receiver === ''}
			<input id="reverse-sig" type="checkbox" bind:checked={reverseSig} disabled />
		{:else}
			<input id="reverse-sig" type="checkbox" bind:checked={reverseSig} />
			<label for="reverse-sig">Include reverse signaling</label>
		{/if}
	</div>
	<!-- Intrascore filter -->
	<br />
	<div class="flex items-center gap-2">
		<input id="intra-filter" type="checkbox" bind:checked={filterIntrascore} />
		<label for="intra-filter">Filter by intrascore</label>
	</div>
	{#if filterIntrascore}
		<div class="flex flex-col gap-1">
			<label for="intra-min-tresh">Min: {minIntrascore}</label>
			<input
				id="intra-min-tresh"
				type="range"
				min="0"
				max="1"
				step="0.01"
				bind:value={minIntrascore}
			/>
			<br />
			<label for="intra-max-tresh">Max: {maxIntrascore}</label>
			<input
				id="intra-max-tresh"
				type="range"
				min="0"
				max="1"
				step="0.01"
				bind:value={maxIntrascore}
			/>
		</div>
	{/if}
	<!-- Significance filter -->
	<div class="flex items-center gap-2">
		<input id="pv-filter" type="checkbox" bind:checked={filterPv} />
		<label for="pv-filter">Filter by significance (p-value)</label>
	</div>
	{#if filterPv}
		<div>
			<label for="pv-thresh">Threshold: {pvThresh}</label>
			<input
				id="pv-thresh"
				type="number"
				step="0.001"
				min="0"
				max="1"
				bind:value={pvThresh}
				class="border rounded p-1 w-full"
			/>
		</div>
	{/if}
	<!-- Inter CCC score direction filter -->
	<div class="flex items-center gap-2">
		<input id="inter-filter" type="checkbox" bind:checked={filterInter} />
		<label for="inter-filter">Filter by differential CCC</label>
	</div>
	{#if filterInter}
		<div class="flex gap-2">
			<label><input type="radio" value="up" bind:group={interDir} /> Up</label>
			<label><input type="radio" value="down" bind:group={interDir} /> Down</label>
		</div>
	{/if}
	<!-- Apply button -->
	<br />
	{#if sender === '' || receiver === ''}
		<button
			id="apply-filters-btn"
			type="button"
			class="btn btn-dark disabled"
			on:click={applyFilters}
			style="float: center;"
		>
			Apply filters
		</button>
	{:else}
		<button
			id="apply-filters-btn"
			type="button"
			class="btn btn-dark"
			on:click={applyFilters}
			style="float: center;"
		>
			Apply filters
		</button>
	{/if}

	<br />
	{#if filtersApplied}<span class="badge bg-success">Selected celltypes: {sender}, {receiver}</span
		>{/if}
</div>
