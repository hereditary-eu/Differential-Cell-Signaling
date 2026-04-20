<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		sender,
		receiver,
		reverseSig,
		colorScale,
		aesLRMapping,
		aesTFMapping
	} from '$lib/stores';
	import {
		zoomBehavior,
		width,
		height,
		drawShape,
		highlightNode,
		drawLegend,
		aesEdge,
		defineMarkers,
		trimPath
	} from './utils';

	export let networkData: { nodes: any[]; links: any[] };
	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;

	function renderNetwork() {
		if (!networkData?.nodes?.length) return;
		simulation?.stop();
		console.log('aesTFMapping in NetworkCircular:', $aesTFMapping);
		const nodes = networkData.nodes.map((d) => ({ ...d }));
		const links = networkData.links.map((d) => ({ ...d }));

		d3.select(svgContainer).selectAll('*').remove(); // clear previous renderings

		// helper to identify nodes location
		function isInnerCircle(d: any) {
			return d.moltype === 'TF' && d.celltype === $sender;
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

		// create the svg DOM element
		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, width, height])
			.style('background', 'transparent')
			.style('cursor', 'grab');
		defineMarkers(svg); // define markers for TFL
		const zoomLayer = svg.append('g');
		const { zoom, initialTransform } = zoomBehavior(zoomLayer);
		svg.call(zoom as any); // attach zoom to svg
		svg.call(zoom.transform as any, initialTransform); // apply initial position
		//center of draw
		const cx = width / 2;
		const cy = height / 2;

		// draw circles
		var innerCircleRadius = 130;
		var incrementRadius = 110;
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
			.attr('stroke', '#ababab')
			.attr('stroke-dasharray', '4 2');

		simulation = d3
			.forceSimulation(nodes)
			.force(
				'link',
				d3
					.forceLink(links)
					.id((d: any) => d.id)
					// .distance(15)
					.strength(0.1)
			)
			.force('charge', d3.forceManyBody().strength(-23))
			.force('center', d3.forceCenter(width / 2, height / 2));

		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke-opacity', 0.6)
			.selectAll('path')
			.data(links)
			.join('path');

		const node = zoomLayer
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1.5)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.call((selection) => drawShape(selection, $colorScale)) // map shape to moltype
			.on('click', (event: any, d: { id: string }) => highlightNode(d.id, links, node, link));

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
				// .toFixed is for rounding decimal to third position
				return `${d.type} (${d.source.name} → ${d.target.name}) weight: ${d.weight.toFixed(3)} significance: ${d.significance.toFixed(3)}`;
			} else {
				return `${d.type} (${d.source.name} → ${d.target.name})`;
			}
		});

		//update positions during simulation
		simulation.on('tick', () => {
			nodes.forEach((d) => {
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

			node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);

			link
				.attr('d', (d: any) => {
					let end = { x: d.target.x, y: d.target.y };
					if (d.type === 'TFL' && $aesTFMapping === 'endShape') {
						end = trimPath(d.source, d.target, 10);
					}
					const dx = d.target.x - d.source.x;
					const dy = d.target.y - d.source.y;
					const dr = Math.sqrt(dx * dx + dy * dy) * 0.99; // adjust curvature
					return `
					M ${d.source.x},${d.source.y}
					A ${dr},${dr} 0 0 1 ${end.x},${end.y}
				`;
				})
				.call((selection) => aesEdge(selection, $aesLRMapping, $aesTFMapping));
		});
		drawLegend(svgContainer, $colorScale, $aesLRMapping, $aesTFMapping);
	}

	$: if (networkData && networkData.nodes && $aesLRMapping && $aesTFMapping) {
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
