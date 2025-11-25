<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';

	export let networkData: { nodes: any[]; links: any[] };

	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let width = 1000;
	let height = 700;

	const colorScale = d3.scaleOrdinal(d3.schemeTableau10);

	function renderNetwork() {
		if (!networkData?.nodes?.length) return;

		const nodes = networkData.nodes.map((d) => ({ ...d }));
		const links = networkData.links.map((d) => ({ ...d }));

		d3.select(svgContainer).selectAll('*').remove(); // Clear previous renderings

		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, width, height])
			.style('background', '#fafafa')
			.style('cursor', 'grab');

		// Build force layout
		simulation = d3
			.forceSimulation(nodes)
			.force(
				'link',
				d3
					.forceLink(links)
					.id((d: any) => d.id)
					.distance(80)
					.strength(0.2)
			)
			.force('charge', d3.forceManyBody().strength(-150))
			.force('center', d3.forceCenter(width / 2, height / 2));

		// Draw links
		const link = svg
			.append('g')
			.attr('stroke', '#999')
			.attr('stroke-opacity', 0.6)
			.selectAll('line')
			.data(links)
			.join('line');

		// Draw nodes
		const node = svg
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1.5)
			.selectAll('circle')
			.data(nodes)
			.join('circle')
			.attr('fill', (d: any) => colorScale(d.celltype));

		// Tooltip
		node.append('title').text((d: any) => `${d.name} (${d.celltype})`);

		// Tick updates
		simulation.on('tick', () => {
			link
				.attr('x1', (d: any) => d.source.x)
				.attr('y1', (d: any) => d.source.y)
				.attr('x2', (d: any) => d.target.x)
				.attr('y2', (d: any) => d.target.y);

			node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
		});
	}

	// Watch for new data
	$: if (networkData && networkData.nodes) {
		renderNetwork();
	}

	onMount(() => {
		renderNetwork();
	});

	onDestroy(() => {
		simulation?.stop();
	});
</script>

<svg bind:this={svgContainer} class="w-full h-full" overflow="scroll"></svg>
