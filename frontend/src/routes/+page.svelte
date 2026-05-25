<script lang="ts">
	import SidebarFilter from './SidebarFilter.svelte';
	import SidebarCaseStudies from './SidebarCaseStudies.svelte';
	import SidebarQuery from './SidebarQuery.svelte';
	import SidebarSearch from './SidebarSearch.svelte';
	import NetworkGraphZoom from './NetworkGraphZoom.svelte';
	import NetworkCircular from './NetworkCircular.svelte';
	import NetworkHive from './NetworkHive.svelte';
	import FullNetwork from './NetworkFull.svelte';
	import VisSeparateOverview from './OverviewVis.svelte';
	import NetworkTree from './NetworkTree.svelte';
	import GOEAResults from './GOEAresults.svelte';

	import {
		celltypes,
		sender,
		receiver,
		selectedCaseStudy,
		selectedComparison,
		selectedNode,
		selectedNodeName,
		aesSettings,
		goResults
	} from '$lib/stores';

	const backend = import.meta.env.VITE_BACKEND_URL ?? ''; // for deployment fallback to empty string

	interface NetworkStats {
		nNodes: number;
		nLigands: number;
		nReceptors: number;
		nTFs: number;
		nLinks: number;
		nLRLinks: number;
		nTFLLinks: number;
		nRTFLinks: number;
		b_outlierThreshold: number;
		p_outlierThreshold: number;
		b_topMols: any[];
		p_topMols: any[];
	}
	let networkData = $state({
		nodes: [],
		links: [],
		stats: {} as NetworkStats,
		p_top3Mols: [],
		b_top3Mols: []
	});
	let fullNet = $state({
		nodes: [],
		links: [],
		stats: {} as NetworkStats,
		celltypes: [],
		total_nodes: 0,
		total_links: 0,
		heatmaps: {
			lr_heatmap: { data: [], sender_totals: {}, receiver_totals: {} },
			tfl_heatmap: { data: [] },
			rtf_heatmap: { data: [] }
		},
		initialize: { sender: '', receiver: '' }
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
			sender.set(fullNet.initialize.sender);
			receiver.set(fullNet.initialize.receiver);
		} catch (err) {
			console.error('Error loading full network:', err);
		}
	}

	async function loadFilteredData(url: string) {
		try {
			const res = await fetch(url);
			networkData = await res.json();
			console.log('from loadFilteredData: ', networkData.p_top3Mols[0]['id']);
			selectedNode.set(networkData.p_top3Mols[0]['id']);
			selectedNodeName.set(networkData.p_top3Mols[0]['name']);
		} catch (err) {
			console.error('Error loading data:', err);
		}
	}
	// handle download svg for sender-receiver vis
	type DownloadableNetworkRef = { expdownloadSVG: () => Promise<void> | void };
	let zoomRef: DownloadableNetworkRef | null = null;
	let circularRef: DownloadableNetworkRef | null = null;
	let hiveRef: DownloadableNetworkRef | null = null;
	let activeTab = 'network-zoom';
	async function downloadCurrentNetwork() {
		if (activeTab === 'network-zoom') {
			await zoomRef?.expdownloadSVG();
		} else if (activeTab === 'network-circular') {
			await circularRef?.expdownloadSVG();
		} else if (activeTab === 'network-hive') {
			await hiveRef?.expdownloadSVG();
		} else {
			console.warn('No active network visualization to download.');
		}
	}
</script>

<div class="app">
	<div class="d-flex">
		<aside
			class="bg-light border-end"
			style="width: 20%; position: sticky; top: 0; height: 100vh; overflow-y: auto;"
		>
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
							<br />
							<p class="card-text">
								N. cell types: {$celltypes.length} <br />
								Total nodes: {fullNet.total_nodes} <br />
								Total links: {fullNet.total_links} <br />
							</p>
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
							<hr />
							<ul>
								<li>Filtered nodes: {networkData.stats.nNodes}</li>
								<ul>
									<li>Ligands: {networkData.stats.nLigands}</li>
									<li>Receptors: {networkData.stats.nReceptors}</li>
									<li>TFs: {networkData.stats.nTFs}</li>
								</ul>
								<li>Filtered links: {networkData.stats.nLinks}</li>
								<ul>
									<li>LR links: {networkData.stats.nLRLinks}</li>
									<li>TFL links: {networkData.stats.nTFLLinks}</li>
									<li>RTF links: {networkData.stats.nRTFLinks}</li>
								</ul>
							</ul>
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
			<svg width="0" height="0" style="position:absolute; pointer-events:none;">
				<defs>
					<marker
						id="arrow"
						viewBox="0 -5 10 10"
						refX="9"
						refY="0"
						markerWidth="6"
						markerHeight="6"
						orient="auto"
					>
						<path d="M0,-5L10,0L0,5" fill="#999" />
					</marker>
					<marker
						id="Tblunt"
						viewBox="-2 -6 4 12"
						refX="1"
						refY="0"
						markerWidth="10"
						markerHeight="10"
						orient="auto"
					>
						<path d="M0,-6L0,6" stroke="#999" stroke-width="2" />
					</marker>
					<marker
						id="leg-arrow"
						viewBox="0 -3 6 6"
						refX="5"
						refY="0"
						markerWidth="4"
						markerHeight="4"
						orient="auto"
					>
						<path d="M0,-3L6,0L0,3" fill="#999" />
					</marker>
					<marker
						id="leg-blunt"
						viewBox="-2 -4 4 8"
						refX="1"
						refY="0"
						markerWidth="6"
						markerHeight="6"
						orient="auto"
					>
						<line x1="0" y1="-4" x2="0" y2="4" stroke="#999" stroke-width="1.5" />
					</marker>
				</defs>
			</svg>
			<div style="display: flex; align-items: flex-start; gap: 1%; width: 100%;">
				<!-- full net -->
				<div
					class="card border-primary mb-3"
					style="width: 60%; height: 60dvh; display: flex; flex-direction: column;"
				>
					<p class="card-header">Full Network for {$selectedCaseStudy} : {$selectedComparison}</p>
					<div style="flex: 1; min-height: 0; overflow-y: hidden;">
						<FullNetwork {fullNet} />
					</div>
				</div>
				<!-- overview -->
				<div
					class="card border-primary mb-3"
					style="width: 39%; height: 60dvh; display: flex; flex-direction: column;"
				>
					<p class="card-header">Overview</p>
					<div style="flex: 1; min-height: 0; overflow-y: auto">
						<VisSeparateOverview fullNet={fullNet as any} />
					</div>
				</div>
			</div>
			<!-- filtered sender-receiver net -->
			<div style="display: flex; align-items: stretch; gap: 1%; width: 100%; height: 60dvh;">
				<div
					class="card border-primary mb-3"
					style="width: 50%; height: 100%; display: flex; flex-direction: column; min-height: 0;"
				>
					<ul class="nav nav-tabs" role="tablist">
						<li class="nav-item" role="presentation">
							<a
								class="nav-link active"
								data-bs-toggle="tab"
								href="#network-zoom"
								role="tab"
								onclick={() => (activeTab = 'network-zoom')}>Network</a
							>
						</li>
						<li class="nav-item" role="presentation">
							<a
								class="nav-link"
								data-bs-toggle="tab"
								href="#network-circular"
								role="tab"
								onclick={() => (activeTab = 'network-circular')}>Circular</a
							>
						</li>
						<li class="nav-item" role="presentation">
							<a
								class="nav-link"
								data-bs-toggle="tab"
								href="#network-hive"
								role="tab"
								onclick={() => (activeTab = 'network-hive')}
							>
								Hive
							</a>
						</li>
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
								<a
									class="dropdown-item"
									href="#drop"
									onclick={() => ($aesSettings.CT = !$aesSettings.CT)}>CellTypes color</a
								>
								<div class="dropdown-divider"></div>
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.LR = 'viridis')}
									>LR viridis</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.LR = 'volcano')}
									>LR volcano</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.LR = 'reset')}
									>LR reset</a
								>
								<div class="dropdown-divider"></div>
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.TF = 'endShape')}
									>TFL action</a
								>
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.TF = 'reset')}
									>TFL reset</a
								>
								<div class="dropdown-divider"></div>
								<a
									class="dropdown-item"
									href="#drop"
									onclick={() => ($aesSettings.groupNodes = !$aesSettings.groupNodes)}>Group TFs</a
								>
								<div class="dropdown-divider"></div>
								<a class="dropdown-item" href="#drop" onclick={() => downloadCurrentNetwork()}
									>Download SVG</a
								>
							</div>
						</li>
					</ul>
					<div
						id="tabContainer"
						class="tab-content"
						style="flex: 1; min-height: 0; display: flex; flex-direction: column;"
					>
						<div
							class="tab-pane fade show active"
							id="network-zoom"
							role="tabpanel"
							style="flex: 1; min-height: 0; height: 100%;"
						>
							<NetworkGraphZoom bind:this={zoomRef} {networkData} />
						</div>
						<div
							class="tab-pane fade"
							id="network-circular"
							role="tabpanel"
							style="flex: 1; min-height: 0; height: 100%;"
						>
							<NetworkCircular bind:this={circularRef} {networkData} />
						</div>
						<div
							class="tab-pane fade"
							id="network-hive"
							role="tabpanel"
							style="flex: 1; min-height: 0; height: 100%;"
						>
							<!-- <p style="margin: 1rem;">Hive layout coming soon...</p> -->
							<NetworkHive bind:this={hiveRef} {networkData} />
						</div>
					</div>
				</div>
				<div
					class="card border-primary mb-3"
					style="width: 49%; height: 100%; display: flex; flex-direction: column; min-height: 0;"
				>
					<!-- <p class="card-header">
						{#if $selectedNodeName}Detailed Tree for {$selectedNodeName}{:else}Detailed Tree{/if}
        			</p> -->
					<div style="flex: 1; min-height: 0;">
						{#if $selectedNodeName}
							<NetworkTree />
						{:else}
							<p style="margin: 1rem; color: #888;">Select a node to see its tree.</p>
						{/if}
					</div>
				</div>
			</div>
			<br />
			{#if $goResults}
				<div id="goea-results-panel" class="card border-primary mb-3" style="width: 100%;">
					<p class="card-header d-flex align-items-center gap-2">
						GProfiler ORA Enrichment Analysis Results
						<span class="badge bg-success ms-2">{$goResults?.n_significant} significant terms</span>
						{#if $goResults?.universe_warning}
							<span class="badge bg-warning text-dark ms-1" title={$goResults.universe_warning}
								>Universe warning</span
							>
						{/if}
					</p>
					<div style="min-height: 200px;">
						<GOEAResults />
					</div>
				</div>
			{/if}
		</main>
		<!-- End of d-flex -->
	</div>
	<!-- End of app -->
</div>
