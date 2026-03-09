<script lang="ts">
	import {
		selectedCaseStudy,
		selectedComparison,
		sender,
		receiver,
		reverseSig,
		celltypes,
		filtersApplied
	} from '$lib/stores';
	import { writable } from 'svelte/store';

	const backend = import.meta.env.VITE_BACKEND_URL;

	// Props
	// export let loadFilteredData: (url: string) => Promise<void>;
	const {
		loadFilteredData
	}: {
		loadFilteredData: (url: string) => Promise<void>;
	} = $props();

	let filterIntrascore = false;
	let filterInter = false;
	let filterPv = true;
	let pvThresh: number = 0.05;
	let minIntrascore = 0.5;
	let maxIntrascore = 1.0;
	let interDir: 'up' | 'down' = 'up';
	let focusOnLR = false;
	let lastSender = writable('');
	let lastReceiver = writable('');
	// reset cell types when case study changes
	$effect(() => {
		if ($selectedComparison) {
			resetFilters();
		}
	});
	function resetFilters() {
		// reset cell types
		sender.set($celltypes[0] || '');
		receiver.set($celltypes[0] || '');

		// reset filter toggles
		filterIntrascore = false;
		filterInter = false;
		filterPv = true;
		pvThresh = 0.05;
		minIntrascore = 0.5;
		maxIntrascore = 1.0;
		interDir = 'up';
		focusOnLR = false;

		filtersApplied.set(true);
	}
	function applyFilters() {
		const query = new URLSearchParams({
			comparison: $selectedComparison,
			sender: $sender,
			receiver: $receiver,
			reverse_sig: $reverseSig.toString(),
			filter_intrascore: filterIntrascore.toString(),
			filter_pv: filterPv.toString(),
			filter_inter: filterInter.toString(),
			min_intrascore: minIntrascore.toString(),
			max_intrascore: maxIntrascore.toString(),
			pv_thresh: pvThresh.toString(),
			inter_dir: interDir,
			focus_on_LR: focusOnLR.toString()
		});
		lastSender.set($sender);
		lastReceiver.set($receiver);

		filtersApplied.set(true);
		loadFilteredData(`${backend}/api/filtered_data?${query.toString()}`);
	}
	function updateSender(event: Event) {
		const target = event.target as HTMLSelectElement;
		sender.set(target.value);
	}
	function updateReceiver(event: Event) {
		const target = event.target as HTMLSelectElement;
		receiver.set(target.value);
	}
	function updateReverseSig(event: Event) {
		const target = event.target as HTMLInputElement;
		reverseSig.set(target.checked);
	}
</script>

<div style="margin-left: 3%;">
	<!-- Sidebar for filters -->
	<!--  cell type(s) selection -->
	<div>
		<p class="block mb-1 font-semibold">Select cell types:</p>
		<div class="d-flex">
			<div style="width: 45%; margin-right: 3%;">
				<label for="sender-select">Sender:</label>
				<select
					id="sender-select"
					on:change={updateSender}
					class="border rounded p-2"
					style="width: 100%;"
					bind:value={$sender}
				>
					{#each $celltypes as ct}
						<option value={ct}>{ct}</option>
					{/each}
				</select>
			</div>

			<div style="width: 45%;">
				<label for="receiver-select">Receiver:</label>
				<select
					id="receiver-select"
					on:change={updateReceiver}
					class="border rounded p-2"
					style="width: 100%;"
					bind:value={$receiver}
				>
					{#each $celltypes as ct}
						<option value={ct}>{ct}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>
	<!-- Include also reverse signaling -->
	<div class="flex items-center gap-2">
		{#if $sender === '' || $receiver === ''}
			<input id="reverse-sig" type="checkbox" on:change={updateReverseSig} disabled />
		{:else}
			<input
				id="reverse-sig"
				type="checkbox"
				on:change={updateReverseSig}
				bind:checked={$reverseSig}
			/>
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

	<!-- Focus on LR filter -->
	<div class="flex items-center gap-2">
		<input id="focus-LR" type="checkbox" bind:checked={focusOnLR} />
		<label for="focus-LR">Focus on LR interactions</label>
	</div>

	<!-- Apply button -->
	<br />
	<button
		id="apply-filters-btn"
		type="button"
		class="btn btn-dark"
		on:click={applyFilters}
		disabled={$sender === '' || $receiver === ''}
	>
		Apply filters
	</button>

	<br />
	{#if $filtersApplied}<span class="badge bg-success"
			>Selected cell types: {$lastSender}, {$lastReceiver}</span
		>{/if}
</div>
