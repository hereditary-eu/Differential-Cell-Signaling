<script lang="ts">
	import {
		selectedComparison,
		sender,
		receiver,
		reverseSig,
		celltypes,
		filtersApplied,
		filteringQueryStr
	} from '$lib/stores';

	import { base } from '$app/paths';
	const backend = import.meta.env.VITE_BACKEND_URL ?? base;

	const {
		loadFilteredData
	}: {
		loadFilteredData: (url: string) => Promise<void>;
	} = $props();

	let filterIntrascore = $state(false);
	let filterInter = $state(false);
	let filterPv = $state(true);
	let pvThresh = $state(0.05);
	let minIntrascore = $state(0.5);
	let maxIntrascore = $state(1.0);
	let interDir = $state('up');
	let focusOnLR = $state(true);
	let filterTFs = $state(false);

	let isResetting = false;

	$effect(() => {
		if ($selectedComparison) {
			resetFilters();
		}
	});

	$effect(() => {
		const _ = [
			$sender,
			$receiver,
			$reverseSig,
			filterIntrascore,
			filterInter,
			filterPv,
			pvThresh,
			minIntrascore,
			maxIntrascore,
			interDir,
			focusOnLR,
			filterTFs
		];

		if (!isResetting) {
			applyFilters();
		}
	});

	function resetFilters() {
		isResetting = true;

		// sender.set($celltypes[0] || '');
		// receiver.set($celltypes[0] || '');
		filterIntrascore = false;
		filterInter = false;
		filterPv = true;
		pvThresh = 0.05;
		minIntrascore = 0.5;
		maxIntrascore = 1.0;
		interDir = 'up';
		focusOnLR = true;
		filterTFs = false;

		setTimeout(() => {
			isResetting = false;
			applyFilters();
		}, 0);
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
			focus_on_LR: focusOnLR.toString(),
			filterTFs: filterTFs.toString()
		});
		filteringQueryStr.set(`${query.toString()}`);
		console.log('FILTERING QUERY TO STR');
		console.log(filteringQueryStr);
		filtersApplied.set(true);
		loadFilteredData(`${backend}/api/filtered_data?${query.toString()}`);
	}
</script>

<div style="margin-left: 3%;">
	<!-- Sidebar for filters -->
	<!--  cell type(s) selection -->
	<div>
		<p class="block mb-1 font-semibold">Cell types:</p>
		<div class="d-flex">
			<div style="width: 45%; margin-right: 3%;">
				<label for="sender-select">Sender:</label>
				<select
					id="sender-select"
					class="border rounded p-2"
					style="width: 100%;"
					bind:value={$sender}
					onchange={applyFilters}
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
					class="border rounded p-2"
					style="width: 100%;"
					bind:value={$receiver}
					onchange={applyFilters}
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
			<input id="reverse-sig" type="checkbox" disabled />
		{:else}
			<input id="reverse-sig" type="checkbox" bind:checked={$reverseSig} />
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
				onselect={applyFilters}
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
				onselect={applyFilters}
			/>
		</div>
	{/if}
	<!-- Significance filter -->
	<div class="flex items-center gap-2">
		<input id="pv-filter" type="checkbox" bind:checked={filterPv} />
		<label for="pv-filter">Filter by significance</label>
	</div>
	{#if filterPv}
		<div>
			<label for="pv-thresh">p-value threshold: </label>
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
		<input id="focus-LR" type="checkbox" bind:checked={focusOnLR} defaultChecked />
		<label for="focus-LR">Focus on LR interactions</label>
	</div>
	<div class="flex items-center gap-2">
		<input id="filterTFs" type="checkbox" bind:checked={filterTFs} />
		<label for="filterTFs">Filter TFs</label>
	</div>
</div>
