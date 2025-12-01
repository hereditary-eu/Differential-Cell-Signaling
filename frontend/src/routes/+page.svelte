<script lang="ts">
	import { onMount } from 'svelte';
	import SidebarFilter from './SidebarFilter.svelte';
	// import NetworkGraph from './NetworkGraph.svelte';
	import NetworkGraphZoom from './NetworkGraphZoom.svelte';
	import NetworkCircular from './NetworkCircular.svelte';
	import { celltypes } from '$lib/stores';
	import { scaleOrdinal, schemeTableau10 } from 'd3';

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

	let static_info = $state({ celltypes: [], total_nodes: 0, total_links: 0 });
	let networkData = $state({ nodes: [], links: [], stats: {} as NetworkStats });

	celltypes.update(() => static_info.celltypes);

	let colorScale = $derived(scaleOrdinal(schemeTableau10).domain($celltypes));
	// console.log('COLOR SCALE', $colorScale.domain(), $colorScale.range());

	onMount(async () => {
		const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/static_info`);
		static_info = await res.json();
	});

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
			<div
				class="card border-info mb-3"
				style="max-width: 30%; display: inline-block; margin-right: 1rem;"
			>
				<div class="card-header">Full Network Stats</div>
				<div class="card-body">
					<p class="card-text">
						N. cell types: {$celltypes.length} <br />
						Total nodes: {static_info.total_nodes} <br />
						Total links: {static_info.total_links} <br />
					</p>
				</div>
			</div>

			{#if networkData.nodes.length > 0}
				<div
					class="card border-info mb-3"
					style="max-width: 18%; display: inline-block; margin-right: 1rem;"
				>
					<div class="card-header">N. nodes: {networkData.stats.nNodes}</div>
					<div class="card-body">
						<p class="card-text">
							Ligands: {networkData.stats.nLigands} <br />
							Receptors: {networkData.stats.nReceptors} <br />
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
				<div
					class="alert alert-info"
					role="alert"
					style="max-width: 40%; display: inline-block; vertical-align: top;"
				>
					Apply filters to see network statistics and visualization.
				</div>
			{/if}

			<div class="card border-primary mb-3">
				<ul class="nav nav-tabs" role="tablist">
					<li class="nav-item" role="presentation">
						<a class="nav-link active" data-bs-toggle="tab" href="#network-zoom" role="tab"
							>Classic Graph</a
						>
					</li>
					<li class="nav-item" role="presentation">
						<a class="nav-link" data-bs-toggle="tab" href="#network-circular" role="tab"
							>Concentric Circular</a
						>
					</li>
					<li class="nav-item" role="presentation">
						<a class="nav-link" data-bs-toggle="tab" href="#network-linear" role="tab">Linear</a>
					</li>
					<li class="nav-item" role="presentation">
						<a class="nav-link" data-bs-toggle="tab" href="#network-hive" role="tab">Hive</a>
					</li>
					<li class="nav-item" role="presentation">
						<a class="nav-link" data-bs-toggle="tab" href="#network-tree" role="tab">Tree</a>
					</li>
				</ul>
				<div id="tabContainer" class="tab-content">
					<div class="tab-pane fade show active" id="network-zoom" role="tabpanel">
						<!-- <div style="width: 1000px; height: 300px;"> -->
						<!-- regulate div dims from here -->
						<NetworkGraphZoom {networkData} {colorScale} />
						<!-- </div> -->
					</div>
					<div class="tab-pane fade" id="network-circular" role="tabpanel">
						<NetworkCircular {networkData} {colorScale} />
					</div>
					<div class="tab-pane fade" id="network-hive" role="tabpanel">
						<p style="margin: 1rem;">Hive layout coming soon...</p>
					</div>
					<div class="tab-pane fade" id="network-linear" role="tabpanel">
						<p style="margin: 1rem;">Linear layout coming soon...</p>
					</div>
					<div class="tab-pane fade" id="network-tree" role="tabpanel">
						<p style="margin: 1rem;">Tree layout coming soon...</p>
					</div>
				</div>
				<!-- <div style="width: 1000px; height: 300px;"> -->
				<!-- regulate div dims from here -->
				<!-- <NetworkGraphZoom {networkData} /> -->
				<!-- </div> -->
			</div>
		</main>
		<!-- End of d-flex -->
	</div>
	<!-- End of app -->
</div>
