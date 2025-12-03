<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';

	export let networkData: { nodes: any[]; links: any[] };
	export let colorScale: d3.ScaleOrdinal<string, string, never>;

	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let width = 400;
	let height = 250;

	function drawShape(selection: d3.Selection<any, any, any, any>) {
		selection.each(function (d: any) {
			const g = d3.select(this);

			if (d.moltype === 'TF') {
				g.append('circle').attr('r', 7).attr('fill', colorScale(d.celltype));
			} else if (d.moltype === 'ligand') {
				const size = 90;
				g.append('path')
					.attr('d', d3.symbol().type(d3.symbolTriangle).size(size))
					.attr('fill', colorScale(d.celltype));
			} else if (d.moltype === 'receptor') {
				const side = 12;
				g.append('rect')
					.attr('x', -side / 2)
					.attr('y', -side / 2)
					.attr('width', side)
					.attr('height', side)
					.attr('fill', colorScale(d.celltype));
			}
		});
	}

	function renderNetwork() {
		if (!networkData?.nodes?.length) return;

		const nodes = networkData.nodes.map((d) => ({ ...d }));
		const links = networkData.links.map((d) => ({ ...d }));

		// build adjacency for highlight neibors
		const adjacency: Record<string, Set<string>> = {};
		links.forEach((l: any) => {
			const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
			const targetId = typeof l.target === 'object' ? l.target.id : l.target;
			adjacency[sourceId] = adjacency[sourceId] || new Set<string>();
			adjacency[targetId] = adjacency[targetId] || new Set<string>();
			adjacency[sourceId].add(targetId);
			adjacency[targetId].add(sourceId);
		});
		function getNeighbors(id: string) {
			return adjacency[id] || new Set<string>();
		}
		function highlightNode(selectedId: string) {
			const neighbors = getNeighbors(selectedId);

			node.attr('opacity', (d: any) => (d.id === selectedId || neighbors.has(d.id) ? 1 : 0.1));
			link.attr('opacity', (l: any) =>
				l.source.id === selectedId || l.target.id === selectedId // || //add the following to highlight links starting from neighbor nodes
					? // neighbors.has(l.source.id) ||
						// neighbors.has(l.target.id)
						1
					: 0.1
			);
		}

		d3.select(svgContainer).selectAll('*').remove(); // Clear previous renderings

		// Main SVG
		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, width, height])
			.style('background', 'transparent')
			.style('cursor', 'grab');

		// WRAPPER that zoom/pan will transform
		const zoomLayer = svg.append('g');

		// Zoom behavior
		svg.call(
			d3
				.zoom<SVGSVGElement, unknown>()
				.scaleExtent([0.02, 8]) // min and max zoom
				.on('zoom', (event) => {
					zoomLayer.attr('transform', event.transform);
				})
		);

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
			.attr('stroke', '#999')
			.attr('fill', 'none')
			.attr('stroke-opacity', 0.6)
			// .attr('marker-end', mapNumLinkAttrs) // 'url(#arrow)'
			.selectAll('path')
			.data(links)
			.join('path');

		// draw nodes
		const node = zoomLayer
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1.5)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.join('g')
			.call(drawShape) // map shape to moltype
			.on('click', (event: any, d: { id: string }) => highlightNode(d.id));

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

		// Update positions during simulation
		simulation.on('tick', () => {
			// link
			// 	.attr('x1', (d: any) => d.source.x)
			// 	.attr('y1', (d: any) => d.source.y)
			// 	.attr('x2', (d: any) => d.target.x)
			// 	.attr('y2', (d: any) => d.target.y);
			link.attr('d', (d: any) => {
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy); // radius for arc
				// const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // increase curvature by multiplying
				return `
					M ${d.source.x},${d.source.y}
					A ${dr},${dr} 0 0 1 ${d.target.x},${d.target.y}
				`;
			});
			node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
		});
	}

	// Redraw when data changes
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

<svg bind:this={svgContainer}></svg>
