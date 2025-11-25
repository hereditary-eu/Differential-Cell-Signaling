<script lang="ts">
	import SidebarFilter from './SidebarFilter.svelte';
	// import NetworkGraph from './NetworkGraph.svelte';
	import NetworkGraphZoom from './NetworkGraphZoom.svelte';

	interface NetworkStats {
		nNodes: number;
		nLigands: number;
		nReceptors: number;
		nTFs: number;
		nLinks: number;
		nLRLinks: number;
		nTFLLinks: number;
		nRTFLinks: number;
	}
	// let apiUrl = import.meta.env.VITE_BACKEND_URL + '/api/filtered_data';
	let networkData = { nodes: [], links: [], stats: {} as NetworkStats };
	// let sidebarOpen = true;

	async function loadData(url: string) {
		const res = await fetch(url);
		networkData = await res.json();
		// console.log('Fetched data from:', url);
	}
</script>

<div class="app">
	<div class="d-flex">
		<aside class="bg-light border-end" style="width: 25%;">
			<SidebarFilter on:filter={(e) => loadData(e.detail.url)} />
		</aside>
		<main class="flex-grow-1 p-4" id="graph-area">
			<!-- <span class="badge rounded-pill bg-info"
				>N. nodes after filtering: {networkData.stats.nNodes}</span
			>
			<span class="badge rounded-pill bg-info">N. ligands: {networkData.stats.nLigands}</span>
			<span class="badge rounded-pill bg-info"
				>N. links after filtering: {networkData.stats.nLinks}</span
			> -->
			{#if networkData}
				<div
					class="card border-info mb-3"
					style="max-width: 18%; display: inline-block; margin-right: 1rem;"
				>
					<div class="card-header">N. nodes: {networkData.stats.nNodes}</div>
					<div class="card-body">
						<p class="card-text">
							ligands: {networkData.stats.nLigands} <br />
							receptors: {networkData.stats.nReceptors} <br />
							TFs: {networkData.stats.nTFs} <br />
						</p>
					</div>
				</div>
				<div class="card border-info mb-3" style="max-width: 18%; display: inline-block;">
					<div class="card-header">N. links: {networkData.stats.nLinks}</div>
					<div class="card-body">
						<p class="card-text">
							LR links: {networkData.stats.nLRLinks} <br />
							TFL links: {networkData.stats.nTFLLinks} <br />
							RTF links: {networkData.stats.nRTFLinks} <br />
						</p>
					</div>
				</div>
				<br />
			{:else}
				<div class="alert alert-info" role="alert">
					Apply filters to see network statistics and visualization.
				</div>
			{/if}
			<!-- <NetworkGraph {networkData} /> -->
			<!-- regulate div dims from here -->
			<div style="width: 1000px; height: 300px;">
				<NetworkGraphZoom {networkData} />
			</div>
		</main>
		<!-- End of d-flex -->
	</div>
	<!-- End of app -->
</div>

<!-- <style>
	.app {
		display: flex;
		height: 100vh;
	}

	/* Sidebar */
	aside {
		width: 250px;
		background: white;
		color: grey;
		transition: width 0.3s;
		overflow: hidden;
	}

	aside.collapsed {
		width: 60px;
	}

	/* Main plot area */
	main {
		flex: 1;
		overflow: hidden;
	}
</style> -->
