<script lang="ts">
	import SidebarFilter from './SidebarFilter.svelte';
	import SidebarCaseStudies from './SidebarCaseStudies.svelte';
	import SidebarQuery from './SidebarQuery.svelte';
	import SidebarSearch from './SidebarSearch.svelte';
	import NetworkGraphZoom from './NetworkGraphZoom.svelte';
	import NetworkCircular from './NetworkCircular.svelte';
	import FullNetwork from './NetworkFull.svelte';
	import VisSeparateOverview from './OverviewVis.svelte';
	import NetworkTree from './NetworkTree.svelte';

	import {
		celltypes,
		sender,
		receiver,
		selectedCaseStudy,
		selectedComparison,
		selectedNode,
		selectedNodeName,
		aesSettings
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
		b_outlierThreshold: number;
		p_outlierThreshold: number;
		b_topMols: any[];
		p_topMols: any[];
	}
	let networkData = $state({ nodes: [], links: [], stats: {} as NetworkStats, p_top3Mols: [], b_top3Mols: [] });
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
			console.log('from loadFilteredData: ', networkData.p_top3Mols[0]['id'])
			selectedNode.set(networkData.p_top3Mols[0]['id']);
			selectedNodeName.set(networkData.p_top3Mols[0]['name'])
		} catch (err) {
			console.error('Error loading data:', err);
		}
	}

</script>

<div class="app">
	<div class="d-flex">
		<aside class="bg-light border-end" style="width: 20%; position: sticky; top: 0; height: 100vh; overflow-y: auto;">
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
				<div
					class="card border-primary mb-3"
					style="width: 60%; height: 550px; display: flex; flex-direction: column;"
				>
					<p class="card-header">Full Network for {$selectedCaseStudy} : {$selectedComparison}</p>
					<div style="flex: 1; min-height: 0; overflow-y: auto;">
						<FullNetwork {fullNet} />
					</div>
				</div>

				<div
					class="card border-primary mb-3"
					style="width: 39%; height: 550px; display: flex; flex-direction: column;"
				>
					<p class="card-header">Overview</p>
					<div style="flex: 1; min-height: 0; overflow-y: auto">
						<VisSeparateOverview fullNet={fullNet as any} maxHeight={480} />
					</div>
				</div>
			</div>
			<!-- filtered sender-receiver net -->
			<div style="display: flex; align-items: flex-start; gap: 1%; width: 100%;">
				<div
					class="card border-primary mb-3"
					style="width: 50%; height: 550px; display: flex; flex-direction: column;"
				>
					<ul class="nav nav-tabs" role="tablist">
						<li class="nav-item" role="presentation">
							<a class="nav-link active" data-bs-toggle="tab" href="#network-zoom" role="tab"
								>Network</a
							>
						</li>
						<li class="nav-item" role="presentation">
							<a class="nav-link" data-bs-toggle="tab" href="#network-circular" role="tab"
								>Circular</a
							>
						</li>
						<li class="nav-item" role="presentation">
							<a class="nav-link" data-bs-toggle="tab" href="#network-hive" role="tab">Hive</a>
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
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.CT = !$aesSettings.CT)}
									>CellTypes color</a
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
								<a class="dropdown-item" href="#drop" onclick={() => ($aesSettings.groupNodes = !$aesSettings.groupNodes)}
									>Group Nodes</a
								>
							</div>
						</li>
					</ul>
					<div id="tabContainer" class="tab-content" style="flex: 1; min-height: 0; overflow: hidden;">
						<div class="tab-pane fade show active" id="network-zoom" role="tabpanel" style="height: 100%;">
							<NetworkGraphZoom {networkData} />
						</div>
						<div class="tab-pane fade" id="network-circular" role="tabpanel" style="height: 100%;">
							<NetworkCircular {networkData} />
						</div>
						<div class="tab-pane fade" id="network-hive" role="tabpanel" style="height: 100%;">
							<p style="margin: 1rem;">Hive layout coming soon...</p>
						</div>
					</div>
				</div>
				<div
					class="card border-primary mb-3"
					style="width: 49%; height: 550px; display: flex; flex-direction: column;"
				>
					{#if $selectedNodeName}
						<p class="card-header">Detailed Tree for {$selectedNodeName}</p>
						<NetworkTree />
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
