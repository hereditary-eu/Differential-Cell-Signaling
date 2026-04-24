<script lang="ts">
	import SidebarFilter from './SidebarFilter.svelte';
	import SidebarCaseStudies from './SidebarCaseStudies.svelte';
	import SidebarQuery from './SidebarQuery.svelte';
	import SidebarSearch from './SidebarSearch.svelte';
	import NetworkGraphZoom from './NetworkGraphZoom.svelte';
	import NetworkCircular from './NetworkCircular.svelte';
	import FullNetwork from './NetworkFull.svelte';
	import VisSeparateOverview from './OverviewVis.svelte';

	import {
		celltypes,
		sender,
		receiver,
		selectedCaseStudy,
		selectedComparison,
		selectedNode,
		neighborhoodData,
		aesLRMapping,
		aesTFMapping,
		colorCT,
		molecules
	} from '$lib/stores';

	const backend = import.meta.env.VITE_BACKEND_URL;

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
	let networkData = $state({ nodes: [], links: [], stats: {} as NetworkStats });
	let fullNet = $state({
		nodes: [],
		links: [],
		stats: {} as NetworkStats,
		celltypes: [],
		total_nodes: 0,
		total_links: 0,
		heatmaps: {
			lr_heatmap: { data: {}, sender_totals: {}, receiver_totals: {} },
			tfl_heatmap: { data: {} },
			rtf_heatmap: { data: {} }
		}
	});

	$effect(() => {
		if ($selectedComparison) {
			loadFullNetwork();
		}
	});
	async function loadFullNetwork() {
		try {
			const statusRes = await fetch(
				`${backend}/api/centrality_status?comparison=${$selectedComparison}`
			);
			const { computed } = await statusRes.json();
			if (!computed) {
				await fetch(`${backend}/api/precompute?comparison=${$selectedComparison}`, {
					method: 'POST'
				});
			}
			const res = await fetch(`${backend}/api/full_net?comparison=${$selectedComparison}`);
			fullNet = await res.json();
			celltypes.set(fullNet.celltypes);
		} catch (err) {
			console.error('Error loading full network:', err);
		}
	}

	async function loadFilteredData(url: string) {
		try {
			const res = await fetch(url);
			networkData = await res.json();
		} catch (err) {
			console.error('Error loading data:', err);
		}
	}
	// update selectedNode and pass neighboorhoodData to detailed view
	$effect(() => {
		if ($selectedNode) {
			fetchNeighborhood($selectedNode);
		}
	});
	async function fetchNeighborhood(nodeId: string) {
		if (!$sender || !$receiver) return;
		try {
			const res = await fetch(
				`${backend}/api/neighborhood?comparison=${$selectedComparison}&sender=${$sender}&receiver=${$receiver}&node_id=${nodeId}`
			);
			const data = await res.json();
			neighborhoodData.set(data);
		} catch (err) {
			console.error('Error fetching neighborhood data:', err);
		}
	}
</script>

<div class="app">
	<div class="d-flex">
		<aside class="bg-light border-end" style="width: 24%;">
			<div class="accordion" id="leftSidebarAccordion">
				<div class="accordion-item">
					<h2 class="accordion-header" id="CaseStudies">
						<button
							class="accordion-button collapsed"
							type="button"
							data-bs-toggle="collapse"
							data-bs-target="#collapseCaseStudies"
							aria-expanded="true"
							aria-controls="collapseCaseStudies"
						>
							Case Studies
						</button>
					</h2>
					<div
						id="collapseCaseStudies"
						class="accordion-collapse collapse"
						aria-labelledby="CaseStudies"
						data-bs-parent="#leftSidebarAccordion"
					>
						<div class="accordion-body">
							<SidebarCaseStudies />
						</div>
					</div>
				</div>
				<div class="accordion-item">
					<h2 class="accordion-header" id="Filters">
						<button
							class="accordion-button"
							type="button"
							data-bs-toggle="collapse"
							data-bs-target="#collapseFilters"
							aria-expanded="false"
							aria-controls="collapseFilters"
						>
							Filters Settings
						</button>
					</h2>
					<div
						id="collapseFilters"
						class="accordion-collapse collapse show"
						aria-labelledby="Filters"
						data-bs-parent="#leftSidebarAccordion"
						style=""
					>
						<div class="accordion-body">
							<SidebarFilter {loadFilteredData} />
						</div>
					</div>
				</div>
				<div class="accordion-item">
					<h2 class="accordion-header" id="Search">
						<button
							class="accordion-button collapsed"
							type="button"
							data-bs-toggle="collapse"
							data-bs-target="#collapseSearch"
							aria-expanded="false"
							aria-controls="collapseSearch"
						>
							Name Search
						</button>
					</h2>
					<div
						id="collapseSearch"
						class="accordion-collapse collapse"
						aria-labelledby="Search"
						data-bs-parent="#leftSidebarAccordion"
					>
						<div class="accordion-body">
							<SidebarSearch />
						</div>
					</div>
				</div>
				<div class="accordion-item">
					<h2 class="accordion-header" id="Query">
						<button
							class="accordion-button collapsed"
							type="button"
							data-bs-toggle="collapse"
							data-bs-target="#collapseQuery"
							aria-expanded="false"
							aria-controls="collapseQuery"
						>
							Advanced Query
						</button>
					</h2>
					<div
						id="collapseQuery"
						class="accordion-collapse collapse"
						aria-labelledby="Query"
						data-bs-parent="#leftSidebarAccordion"
					>
						<div class="accordion-body">
							<SidebarQuery />
						</div>
					</div>
				</div>
			</div>
		</aside>
		<main class="flex-grow-1 p-4" id="graph-area">
		<div style="display: flex; align-items: flex-start; gap: 1%; width: 100%;">
			<!-- full net -->
			<div class="card border-primary mb-3" 
			style="width: 65%; height: 550px; display: flex; flex-direction: column;">
				<p class="card-header">Full Network for {$selectedCaseStudy} : {$selectedComparison}</p>
				<div style="flex: 1; min-height: 0; overflow-y: auto;">
				<FullNetwork {fullNet} />
				</div>
			</div>

			<div
				class="card border-primary mb-3"
				style="width: 34%; height: 550px; display: flex; flex-direction: column;"
			>
				<p class="card-header">Overview </p>
				<div style="flex: 1; min-height: 0; overflow-y: auto">
				<VisSeparateOverview {fullNet} maxHeight={480} />
				</div>
			</div>
			</div>
			<!-- filtered sender-receiver net -->
			<div style="display: flex; align-items: flex-start; gap: 1%; width: 100%;">
				<div
					class="card border-primary mb-3"
					style="width: 65%; height: 550px; display: flex; flex-direction: column;"
				>
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
						<!-- <li class="nav-item" role="presentation">
							<a class="nav-link" data-bs-toggle="tab" href="#network-linear" role="tab">Linear</a>
						</li> -->
						<li class="nav-item" role="presentation">
							<a class="nav-link" data-bs-toggle="tab" href="#network-hive" role="tab">Hive</a>
						</li>
						<!-- <li class="nav-item" role="presentation">
							<a class="nav-link" data-bs-toggle="tab" href="#network-tree" role="tab">Tree</a>
						</li> -->
						<li class="nav-item dropdown">
							<a
								class="nav-link dropdown-toggle show"
								data-bs-toggle="dropdown"
								href="#drop"
								role="button"
								aria-haspopup="false"
								aria-expanded="false">...</a
							>
							<div class="dropdown-menu" data-bs-popper="static">
								<a class="dropdown-item" href="#drop" onclick={() => ($colorCT = !$colorCT)}
									>CellTypes color</a
								>
								<!-- <input class="form-check-input dropdown-item" type="checkbox" id="colorCTcheck" />
								<label for="colorCTcheck">Cell types color</label> -->
								<div class="dropdown-divider"></div>
								<a class="dropdown-item" href="#drop" onclick={() => aesLRMapping.set('viridis')}
									>LR viridis</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => aesLRMapping.set('volcano')}
									>LR volcano</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => aesLRMapping.set('reset')}
									>LR reset</a
								>
								<div class="dropdown-divider"></div>
								<a class="dropdown-item" href="#drop" onclick={() => aesTFMapping.set('endShape')}
									>TFL action</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => aesTFMapping.set('reset')}
									>TFL reset</a
								>
							</div>
						</li>
					</ul>
					<div id="tabContainer" class="tab-content">
						<div class="tab-pane fade show active" id="network-zoom" role="tabpanel">
							<NetworkGraphZoom {networkData} />
						</div>
						<div class="tab-pane fade" id="network-circular" role="tabpanel">
							<NetworkCircular {networkData} />
						</div>
						<div class="tab-pane fade" id="network-hive" role="tabpanel">
							<p style="margin: 1rem;">Hive layout coming soon...</p>
						</div>
					</div>
				</div>
				<div 
				class="card border-primary mb-3"
				style="width: 34%; height: 550px; display: flex; flex-direction: column;">
					<p class="card-header">Deatiled Tree </p>
					{#if $selectedNode}
						<!-- keeps complaining about possibility of being null -->
						<!-- <NetworkTree neighborhoodData={$neighborhoodData} /> -->
					{/if}
				</div>
			</div>
			<!-- info boxes -->
			<div
				class="card border-info mb-3"
				style="max-width: 30%; display: inline-block; margin-right: 1rem;"
			>
				<div class="card-header">Full Network Stats</div>
				<div class="card-body">
					<p class="card-text">
						N. cell types: {$celltypes.length} <br />
						Total nodes: {fullNet.total_nodes} <br />
						Total links: {fullNet.total_links} <br />
					</p>
				</div>
			</div>
			{#if networkData.nodes.length > 0}
				<div
					class="card border-info mb-3"
					style="max-width: 18%; display: inline-block; margin-right: 1rem;"
				>
					<div class="card-header">Filtered nodes: {networkData.stats.nNodes}</div>
					<div class="card-body">
						<p class="card-text">
							Ligands: {networkData.stats.nLigands} <br />
							Receptors: {networkData.stats.nReceptors} <br />
							TFs: {networkData.stats.nTFs} <br />
						</p>
					</div>
				</div>
				<div class="card border-info mb-3" style="max-width: 18%; display: inline-block;">
					<div class="card-header">Filtered links: {networkData.stats.nLinks}</div>
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
			<!-- end of info boxes -->
		</main>
		<!-- End of d-flex -->
	</div>
	<!-- End of app -->
</div>
