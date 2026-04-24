<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { colorScale, aesLRMapping, aesTFMapping } from '$lib/stores';
	import { zoomBehavior, width, height, drawNode, highlightNode, drawLegend } from './utils';

	export let fullNet: { nodes: any[]; links: any[] };
	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;

	function renderNetwork() {
		const nodes = fullNet.nodes.map((d) => ({ ...d }));
		const links = fullNet.links.map((d) => ({ ...d }));

		d3.select(svgContainer).selectAll('*').remove(); // clear previous renderings

		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, width, height])
			.style('background', 'transparent')
			.style('cursor', 'grab');

		const zoomLayer = svg.append('g');
		const { zoom, initialTransform } = zoomBehavior(zoomLayer);
		svg.call(zoom as any);
		svg.call(zoom.transform as any, initialTransform);

		// force layout
		simulation = d3
			.forceSimulation(nodes)
			.force(
				'link',
				d3
					.forceLink(links)
					.id((d: any) => d.id)
					.distance(10)
					.strength(0.15)
			)
			.force('charge', d3.forceManyBody().strength(-7))
			.force('center', d3.forceCenter(width * 0.8, height / 2))
			.alphaDecay(0.02);

		// draw links
		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke', '#999')
			.attr('stroke-opacity', 0.6)
			.selectAll('path')
			.data(links)
			.join('path');

		// draw nodes
		const node = zoomLayer
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.join('g')
			.call((selection) => drawNode(selection, $colorScale, true)) // map shape to moltype
			.on('click', (event: any, d: { id: string }) => highlightNode(d.id, links, node, link));

		drawLegend(svgContainer, $colorScale, $aesLRMapping, $aesTFMapping, 6, 7, 5, true);

		//reset when clicking on empty space
		svg.on('click', (event) => {
			if (event.target === svg.node()) {
				node.attr('opacity', 1);
				link.attr('opacity', 1);
			}
		});

		// tooltip (for hovering)
		node.append('title').text((d: any) => `${d.name} (${d.celltype}) - ${d.moltype}`);
		link.append('title').text((d: any) => {
			if (d.type === 'LR') {
				return `${d.type} (${d.source.name} → ${d.target.name}) weight: ${d.weight} significance: ${d.significance}`;
			} else {
				return `${d.type} (${d.source.name} → ${d.target.name})`;
			}
		});

		//update positions during simulation
		simulation.on('tick', () => {
			link.attr('d', (d: any) => {
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy); // radius for arc
				return `
					M ${d.source.x},${d.source.y}
					A ${dr},${dr} 0 0 1 ${d.target.x},${d.target.y}
				`;
			});
			node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
		});
	}

	// Redraw when data changes // it works here but not in concentric layout...!
	$: if (fullNet && fullNet.nodes) {
		renderNetwork();
	}

	onMount(() => {
		renderNetwork();
	});

	onDestroy(() => {
		simulation?.stop();
	});
</script>

<svg bind:this={svgContainer}></svg>
