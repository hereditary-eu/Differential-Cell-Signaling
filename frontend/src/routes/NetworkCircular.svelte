<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		sender,
		receiver,
		reverseSig,
		colorScale,
		aesLRMapping,
		aesTFMapping,
		colorCT,
		highlightedNode
	} from '$lib/stores';
	import {
		zoomBehavior,
		width,
		height,
		drawNode,
		highlightNode,
		drawLegend,
		aesEdge,
		defineMarkers,
		trimPath,
		applyHighlightSearch
	} from './utils';

	export let networkData: { nodes: any[]; links: any[] };

	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	//handle search-based hihlighting
	//handle highligthing the node selected with SidebarSearch
	let nodeSelection: any = null;
	let linkSelection: any = null;

	// These survive re-renders
	let ringRadii: number[] = []; // current radius for each ring (px)
	let ringRotations: number[] = []; // cumulative rotation offset per ring (radians)
	// For each node: its angular position relative to its ring's rotation origin.
	//   absolute_angle = nodeBaseAngle[id] + ringRotations[ringIndex]
	// During rotation, ringRotations[i] changes while nodeBaseAngle doesn't
	// So that relative position of nodes stays intact
	const nodeBaseAngle = new Map<string, number>();

	const cx = () => width / 2;
	const cy = () => height / 2;

	function ringCount(): number {
		return $reverseSig ? 6 : 4;
	}
	function ringIndexOf(d: any): number {
		// to do: to handle bothLR and bothRTF, this shall be changed
		if (d.moltype === 'TF' && d.celltype === $sender) return 0;
		if (d.moltype === 'ligand' && d.celltype === $sender) return 1;
		if (d.moltype === 'receptor' && d.celltype === $receiver) return 2;
		if (d.moltype === 'TF' && d.celltype === $receiver) return 3;
		if ($reverseSig) {
			if (d.moltype === 'ligand' && d.celltype === $receiver) return 4;
			if (d.moltype === 'receptor' && d.celltype === $sender) return 5;
		}
		return -1;
	}

	// Place node at (baseAngle + ringRotation) on its ring
	function projectNode(d: any) {
		const ri = ringIndexOf(d);
		if (ri < 0) return; // nodes with unexpected moltype-ct combination will not be included...
		const angle = (nodeBaseAngle.get(d.id) ?? 0) + ringRotations[ri];
		d.x = cx() + ringRadii[ri] * Math.cos(angle);
		d.y = cy() + ringRadii[ri] * Math.sin(angle);
	}
	function recordBaseAngle(d: any) {
		const ri = ringIndexOf(d);
		if (ri < 0) return;
		nodeBaseAngle.set(d.id, Math.atan2(d.y - cy(), d.x - cx()) - ringRotations[ri]);
	}
	function linkPath(d: any): string {
		const end =
			d.type === 'TFL' && $aesTFMapping === 'endShape'
				? trimPath(d.source, d.target, 10)
				: { x: d.target.x, y: d.target.y };
		const dx = end.x - d.source.x;
		const dy = end.y - d.source.y;
		const dr = Math.sqrt(dx * dx + dy * dy) * 0.99;
		return `M ${d.source.x},${d.source.y} A ${dr},${dr} 0 0 1 ${end.x},${end.y}`;
	}

	const renderNetwork = () => {
		console.log('render network called from circular');
		if (!svgContainer) return;
		if (!networkData?.nodes?.length) return;
		simulation?.stop();

		const n = ringCount();
		// Reset ring state only when ring count changes (for reverseSig)
		if (ringRadii.length !== n) {
			ringRadii = Array.from({ length: n }, (_, i) => 130 + i * 110);
			ringRotations = new Array(n).fill(0);
			nodeBaseAngle.clear();
		}

		const nodes = networkData.nodes.map((d) => ({ ...d }));
		const links = networkData.links.map((d) => ({ ...d }));

		// Seed positions: reuse stored layout when possible, random otherwise
		nodes.forEach((d) => {
			const ri = ringIndexOf(d);
			if (ri < 0) return;
			if (!nodeBaseAngle.has(d.id)) {
				const angle = Math.random() * 2 * Math.PI;
				nodeBaseAngle.set(d.id, angle - ringRotations[ri]);
				d.x = cx() + ringRadii[ri] * Math.cos(angle);
				d.y = cy() + ringRadii[ri] * Math.sin(angle);
			} else {
				projectNode(d);
			}
		});

		const svg = d3.select(svgContainer);
		d3.select(svgContainer).selectAll('g').remove();
		d3.select(svgContainer).selectAll('path').remove();

		svg
			.attr('viewBox', [0, 0, width, height])
			.style('background', 'transparent')
			.style('cursor', 'grab');

		defineMarkers(svg); //still not working
		// if switched tab positions, defineMarkers works and doesnt work in NetworkGraphZoom moved to second tab
		// seems to be due to svg dimensions initialized to zero(?)
		const zoomLayer = svg.append('g').attr('class', 'zoom-layer');
		const { zoom, initialTransform } = zoomBehavior(zoomLayer);
		svg.call(zoom as any);
		svg.call(zoom.transform as any, initialTransform);

		// ── circles ─────────────────────────────────────────────────────────
		const circleGroup = zoomLayer.append('g').attr('class', 'guide-circles');
		function syncCircles() {
			circleGroup
				.selectAll<SVGCircleElement, number>('circle')
				.data(d3.range(n))
				.join('circle')
				.attr('cx', cx())
				.attr('cy', cy())
				.attr('fill', 'none')
				.attr('stroke', '#ababab')
				.attr('stroke-dasharray', '4 4')
				.attr('stroke-width', 2)
				.attr('r', (i) => ringRadii[i]);
		}
		syncCircles();

		simulation = d3
			.forceSimulation(nodes)
			.force(
				'link',
				d3
					.forceLink(links)
					.id((d: any) => d.id)
					.strength(0.1)
			)
			.force('charge', d3.forceManyBody().strength(-23))
			.force(
				'collide',
				d3.forceCollide((d: any) => 14)
			)
			.force('center', d3.forceCenter(cx(), cy()));

		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke-opacity', 0.9)
			.attr('stroke-width', 1.5)
			.selectAll('path')
			.data(links)
			.join('path');
		// .call((sel) => aesEdge(sel, $aesLRMapping, $aesTFMapping));
		// link.call((sel) => aesEdge(sel, $aesLRMapping, $aesTFMapping));
		// debug:
		link.each(function (d: any) {
			const el = d3.select(this);
			console.log('type:', d.type, 'marker-end:', el.attr('marker-end'), 'd:', el.attr('d'));
		});
		const node = zoomLayer
			.append('g')
			.attr('stroke', '#fff')
			.attr('stroke-width', 1.5)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.call((sel) => drawNode(sel, $colorScale, $colorCT))
			.on('click', (event: any, d: { id: string }) => highlightNode(d.id, links, node, link));

		svg.on('click', (event) => {
			if (event.target === svg.node()) {
				node.attr('opacity', 1);
				link.attr('opacity', 1);
			}
		});

		node.append('title').text((d: any) => `${d.name} (${d.celltype}) - ${d.moltype}`);
		link
			.append('title')
			.text((d: any) =>
				d.type === 'LR'
					? `LR (${d.source.name} → ${d.target.name}) weight: ${d.weight.toFixed(3)} significance: ${d.significance.toFixed(3)}`
					: `${d.type} (${d.source.name} → ${d.target.name})`
			);

		// The force simulation proposes positions; override by projecting each
		// node back onto its exact ring radius while keeping the angular direction.
		simulation.on('tick', () => {
			nodes.forEach((d) => {
				const ri = ringIndexOf(d);
				if (ri < 0) return;
				const dx = d.x - cx();
				const dy = d.y - cy();
				const dist = Math.sqrt(dx * dx + dy * dy) || 1;
				d.x = cx() + (dx / dist) * ringRadii[ri];
				d.y = cy() + (dy / dist) * ringRadii[ri];
				recordBaseAngle(d); // Record settled angle so subsequent rotations start from here
			});
			node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
			link.attr('d', linkPath);
			link.call((sel) => aesEdge(sel, $aesLRMapping, $aesTFMapping));
		});

		// simulation.on('end', () => {
		// 	link.call((sel) => aesEdge(sel, $aesLRMapping, $aesTFMapping));
		// });

		// Instantly reposition all nodes on ring `ri` using their stored base
		// angles combined with the current ringRotations[ri] and ringRadii[ri].
		// called directly by the drag handlers
		function reprojectRing(ri: number) {
			nodes.forEach((d) => {
				if (ringIndexOf(d) === ri) projectNode(d);
			});
			node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
			link.attr('d', linkPath);
		}

		const handleLayer = zoomLayer.append('g').attr('class', 'ring-handles');
		const ringGs = handleLayer
			.selectAll<SVGGElement, number>('g.ring-g')
			.data(d3.range(n))
			.join('g')
			.attr('class', 'ring-g');

		// One resize handle per ring
		// Rotation never moves this handle, it is always at (cx + radius, cy).
		//   1. Drag start: stop simulation
		//   2. Drag: pointer distance from centre → new ringRadii[i].
		//            reprojectRing(i) repositions nodes (base angles unchanged).
		//            Any ring can be dragged past any other ring freely.
		//   3. Drag end: soft simulation restart so inter-ring links can relax.
		function resizeX(i: number) {
			return cx() + ringRadii[i];
		}
		function resizeY(_: number) {
			return cy();
		}
		const resizeGs = ringGs.append('g').attr('class', 'resize-g');

		const resizeHandle = resizeGs
			.append('circle')
			.attr('r', 9)
			.attr('cx', resizeX)
			.attr('cy', resizeY)
			.attr('fill', '#fff')
			.attr('fill-opacity', 0.9)
			.attr('stroke', '#a9a9a9')
			.attr('stroke-width', 1.5)
			.attr('cursor', 'ew-resize');

		resizeGs
			.append('text')
			.attr('pointer-events', 'none')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'central')
			.attr('font-size', '9px')
			.attr('fill', '#111')
			.text('⇔')
			.attr('x', resizeX)
			.attr('y', resizeY);

		resizeHandle.call(
			(d3.drag<SVGCircleElement, number>() as any)
				.on('start', function (this: SVGCircleElement, _ev: any, _i: number) {
					simulation.stop();
					d3.select(this).attr('stroke', '#ff0').attr('stroke-width', 2.5);
					svg.style('cursor', 'ew-resize');
				})
				.on('drag', function (this: SVGCircleElement, ev: any, i: number) {
					// Pointer distance from centre becomes the new radius (min 40 px)
					ringRadii[i] = Math.max(40, Math.hypot(ev.x - cx(), ev.y - cy()));
					// Reproject only this ring's nodes
					reprojectRing(i);
					syncCircles();
					d3.select<SVGCircleElement, number>(this).attr('cx', resizeX(i));
					resizeGs
						.filter((_: number, j: number) => j === i)
						.select('text')
						.attr('x', resizeX(i));
					// Sync rotate handle, its position depends on radius too
					rotHandle
						.filter((_: number, j: number) => j === i)
						.attr('cx', rotX(i))
						.attr('cy', rotY(i));
					rotGs
						.filter((_: number, j: number) => j === i)
						.select('text')
						.attr('x', rotX(i))
						.attr('y', rotY(i));
				})
				.on('end', function (this: SVGCircleElement, _ev: any, _i: number) {
					d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
					svg.style('cursor', 'grab');
					simulation.alpha(0.15).restart();
				})
		);

		// One rotate handle per ring
		//   1. Drag start: record the pointer's angle from centre and the ring's current rotation.
		//   2. Drag: delta  = atan2(pointer) – atan2(start pointer)
		//            ringRotations[i] = savedRotation + delta
		//            reprojectRing(i) repositions nodes using updated rotation
		//   3. Drag end: soft restart so cross-ring links relax.

		function rotX(i: number) {
			return cx() + ringRadii[i] * Math.cos(-Math.PI / 2 + ringRotations[i]);
		}
		function rotY(i: number) {
			return cy() + ringRadii[i] * Math.sin(-Math.PI / 2 + ringRotations[i]);
		}
		const rotGs = ringGs.append('g').attr('class', 'rotate-g');
		const rotHandle = rotGs
			.append('circle')
			.attr('r', 9)
			.attr('cx', rotX)
			.attr('cy', rotY)
			.attr('fill', '#fff')
			.attr('fill-opacity', 0.9)
			.attr('stroke', '#a9a9a9')
			.attr('stroke-width', 1.5)
			.attr('cursor', 'crosshair');

		rotGs
			.append('text')
			.attr('pointer-events', 'none')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'central')
			.attr('font-size', '11px')
			.attr('fill', '#111')
			.text('↻')
			.attr('x', rotX)
			.attr('y', rotY);

		// Per-ring drag-start snapshots
		const dragStartAngle = new Array<number>(n).fill(0);
		const rotationAtDragStart = new Array<number>(n).fill(0);

		rotHandle.call(
			(d3.drag<SVGCircleElement, number>() as any)
				.on('start', function (this: SVGCircleElement, ev: any, i: number) {
					simulation.stop();
					dragStartAngle[i] = Math.atan2(ev.y - cy(), ev.x - cx());
					rotationAtDragStart[i] = ringRotations[i];
					d3.select(this).attr('stroke', '#ff0').attr('stroke-width', 2.5);
					svg.style('cursor', 'crosshair');
				})
				.on('drag', function (this: SVGCircleElement, ev: any, i: number) {
					const curAngle = Math.atan2(ev.y - cy(), ev.x - cx());
					const delta = curAngle - dragStartAngle[i];
					ringRotations[i] = rotationAtDragStart[i] + delta;
					reprojectRing(i);
					d3.select<SVGCircleElement, number>(this).attr('cx', rotX(i)).attr('cy', rotY(i));
					rotGs
						.filter((_: number, j: number) => j === i)
						.select('text')
						.attr('x', rotX(i))
						.attr('y', rotY(i));
				})
				.on('end', function (this: SVGCircleElement, _ev: any, _i: number) {
					d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
					svg.style('cursor', 'grab');
					simulation.alpha(0.05).restart();
				})
		);
		drawLegend(svgContainer, $colorScale, $aesLRMapping, $aesTFMapping);
		nodeSelection = node;
		linkSelection = link;
		// apply highlight after re-render
		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	};

	onMount(() => {
		//this different onMount logic is a desperate attempt to solve the markers problem.
		// Check if already visible
		if (svgContainer?.closest('.tab-pane')?.classList.contains('show')) {
			renderNetwork();
		}

		// Also render when tab becomes visible
		const handler = (e: any) => {
			if (e.target?.getAttribute('href') === '#network-circular') {
				renderNetwork();
			}
		};
		document.addEventListener('shown.bs.tab', handler);
		return () => document.removeEventListener('shown.bs.tab', handler);
	});
	onDestroy(() => {
		simulation?.stop();
	});
	$: {
		$aesLRMapping;
		$aesTFMapping;
		$colorCT;
		if (
			networkData?.nodes?.length &&
			svgContainer?.closest('.tab-pane')?.classList.contains('show')
		) {
			renderNetwork();
		}
	}
	$: applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
</script>

<svg bind:this={svgContainer}></svg>
