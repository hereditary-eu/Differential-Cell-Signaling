<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { sender, receiver, reverseSig } from '$lib/stores';
	export let networkData: { nodes: any[]; links: any[] };
	export let colorScale: d3.ScaleOrdinal<string, string, never>; // get the value from parent (+page.svelte)

	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let width = 500;
	let height = 300;

	function drawShape(selection: d3.Selection<any, any, any, any>) {
		selection.each(function (d: any) {
			const g = d3.select(this);

			if (d.moltype === 'TF') {
				g.append('circle').attr('r', 7).attr('fill', colorScale(d.celltype));
			} else if (d.moltype === 'ligand') {
				const size = 80;
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
				l.source.id === selectedId || l.target.id === selectedId ? 1 : 0.1
			);
		}
		// helper to identify nodes location
		function isInnerCircle(d: any) {
			return (
				d.moltype === 'TF' && d.celltype === $sender
				// eventually need to fix by checking type of links associated to TF (to handle autocrine cases)
				//&& d.links?.some((l: any) => l.type === 'TFL')
			);
		}
		function isSecondCircle(d: any) {
			return d.moltype === 'ligand' && d.celltype === $sender;
		}
		function isThirdCircle(d: any) {
			return d.moltype === 'receptor' && d.celltype === $receiver;
		}
		function isFourthCircle(d: any) {
			return d.moltype === 'TF' && d.celltype === $receiver;
		}
		function isFifthCircle(d: any) {
			return d.moltype === 'ligand' && d.celltype === $receiver;
		}
		function isSixthCircle(d: any) {
			return d.moltype === 'receptor' && d.celltype === $sender;
		}
		// Clear previous renderings
		d3.select(svgContainer).selectAll('*').remove();

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
				.scaleExtent([0.2, 7]) // min and max zoom
				.on('zoom', (event) => {
					zoomLayer.attr('transform', event.transform);
				})
		);

		var innerCircleRadius = 100;
		var incrementRadius = 85;

		var circle = zoomLayer
			.selectAll('circle')
			// if not reverseSig, draw 4 circles
			.data($reverseSig ? d3.range(1, 7) : d3.range(1, 5))
			.enter()
			.append('circle')
			.attr('cx', width / 2)
			.attr('cy', height / 2)
			.attr('r', function (d) {
				return innerCircleRadius + (d - 1) * incrementRadius;
			})
			.attr('fill', 'none')
			.attr('stroke', '#ccc')
			.attr('stroke-dasharray', '4 2');

		// Build force layout
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
			.force('charge', d3.forceManyBody().strength(-23))
			.force('center', d3.forceCenter(width / 2, height / 2));

		// Draw links
		const link = zoomLayer
			.append('g')
			.attr('stroke', '#999')
			.attr('fill', 'none')
			.attr('stroke-opacity', 0.6)
			.selectAll('path')
			.data(links)
			.join('path');

		// Draw nodes
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
			nodes.forEach((d) => {
				const cx = width / 2;
				const cy = height / 2;

				// vector from center
				const dx = d.x - cx;
				const dy = d.y - cy;
				const dist = Math.sqrt(dx * dx + dy * dy);

				if (isInnerCircle(d)) {
					if (dist !== innerCircleRadius) {
						const k = innerCircleRadius / dist;
						d.x = cx + dx * k;
						d.y = cy + dy * k;
					}
				} else if (isSecondCircle(d)) {
					const targetRadius = innerCircleRadius + incrementRadius;
					if (dist !== targetRadius) {
						const k = targetRadius / dist;
						d.x = cx + dx * k;
						d.y = cy + dy * k;
					}
				} else if (isThirdCircle(d)) {
					const targetRadius = innerCircleRadius + 2 * incrementRadius;
					if (dist !== targetRadius) {
						const k = targetRadius / dist;
						d.x = cx + dx * k;
						d.y = cy + dy * k;
					}
				} else if (isFourthCircle(d)) {
					const targetRadius = innerCircleRadius + 3 * incrementRadius;
					if (dist !== targetRadius) {
						const k = targetRadius / dist;
						d.x = cx + dx * k;
						d.y = cy + dy * k;
					}
				}
				if ($reverseSig) {
					if (isFifthCircle(d)) {
						const targetRadius = innerCircleRadius + 4 * incrementRadius;
						if (dist !== targetRadius) {
							const k = targetRadius / dist;
							d.x = cx + dx * k;
							d.y = cy + dy * k;
						}
					} else if (isSixthCircle(d)) {
						const targetRadius = innerCircleRadius + 5 * incrementRadius;
						if (dist !== targetRadius) {
							const k = targetRadius / dist;
							d.x = cx + dx * k;
							d.y = cy + dy * k;
						}
					}
				}
			});

			link.attr('d', (d: any) => {
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy);
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
