<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		zoomBehavior,
		width,
		height,
		drawNode,
		drawLegend,
		highlightNode,
		aesEdge,
		trimPath,
		defineMarkers,
		applyHighlightSearch
	} from './utils';
	import {
		colorScale,
		selectedNode,
		highlightedNode,
		aesLRMapping,
		aesTFMapping,
		colorCT
	} from '$lib/stores';

	export let networkData: { nodes: any[]; links: any[] };
	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;

	//handle search-based hihlighting
	//handle highligthing the node selected with SidebarSearch
	let nodeSelection: any = null;
	let linkSelection: any = null;

	function renderNetwork() {
		if (!networkData?.nodes?.length) return;
		simulation?.stop();

		const nodes = networkData.nodes.map((d) => ({ ...d }));
		const links = networkData.links.map((d) => ({ ...d }));

		d3.select(svgContainer).selectAll('*').remove(); // clear previous renderings

		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, width, height])
			.style('background', 'transparent')
			.style('cursor', 'grab');
		defineMarkers(svg); // define markers for TFL
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
					.distance(15)
					.strength(0.1)
			)
			.force('charge', d3.forceManyBody().strength(-10))
			.force('center', d3.forceCenter(width / 2, height / 2));

		// draw links
		const link = zoomLayer
			.append('g')
			.attr('fill', 'none') // without this the area of the arc gets colored
			.attr('stroke-opacity', 0.6)
			.selectAll('path')
			.data(links)
			.join('path')
			.call((selection) => aesEdge(selection, $aesLRMapping, $aesTFMapping));

		// draw nodes
		const node = zoomLayer
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.join('g')
			.call((selection) => drawNode(selection, $colorScale, $colorCT)) // map shape to moltype
			.on('click', (event: any, d: { id: string }) => {
				highlightNode(d.id, links, node, link);
				// selectedNode.set(d.id);
			});

		nodeSelection = node;
		linkSelection = link;

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
				let end = { x: d.target.x, y: d.target.y };
				if (d.type === 'TFL' && $aesTFMapping === 'endShape') {
					end = trimPath(d.source, d.target, 10);
				}
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy); // radius for arc
				// const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // increase curvature by multiplying
				return `
					M ${d.source.x},${d.source.y}
					A ${dr},${dr} 0 0 1 ${end.x},${end.y}
				`;
			});
			node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
		});
		drawLegend(svgContainer, $colorScale, $aesLRMapping, $aesTFMapping);

		// apply highlight after re-render
		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	} //end of renderNetwork()

	// Redraw when data changes
	$: {
		$aesLRMapping;
		$aesTFMapping;
		$colorCT; // add reference to subscribe the rerendering
		if (networkData?.nodes?.length) renderNetwork();
	}

	$: applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);

	onMount(() => {
		renderNetwork();
	});
	onDestroy(() => {
		simulation?.stop();
	});
</script>

<svg bind:this={svgContainer}></svg>
