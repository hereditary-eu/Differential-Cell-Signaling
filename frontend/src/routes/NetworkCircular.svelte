<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		sender,
		receiver,
		reverseSig,
		colorScale,
		aesSettings,
		highlightedNode,
		highlightedCycle,
		selectedNode,
		selectedNodeName
	} from '$lib/stores';
	import {
		drawNode,
		highlightNode,
		deduplicateTFs,
		aesEdge,
		trimPath,
		applyHighlightSearch,
		applyCycleHighlight,
		resetNodesSize,
		updateEdgesAes,
		updateNodeColors
	} from './utils';
	import DrawNetLegend from './drawNetLegend.svelte';
	export let networkData: { nodes: any[]; links: any[] };

	let svgContainer: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let containerDiv: HTMLDivElement;

	let nodeSelection: any = null;
	let linkSelection: any = null;

	let ringRadii: number[] = []; // current radius for each ring (px)
	let ringRotations: number[] = []; // cumulative rotation offset per ring (radians)

	const nodeBaseAngle = new Map<string, number>();

	let _W = 600;
	let _H = 500;
	const cx = () => _W / 2;
	const cy = () => _H / 2;

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
	// function linkPath(d: any): string {
	// 	const src = d.source;
	// 	const end =
	// 		d.type === 'TFL' && $aesSettings.TF === 'endShape'
	// 			? trimPath(d.source, d.target, 10)
	// 			: { x: d.target.x, y: d.target.y };
	// 	// const dx = end.x - d.source.x;
	// 	// const dy = end.y - d.source.y;
	// 	// const dr = Math.sqrt(dx * dx + dy * dy) * 0.99;
	// 	const beta = 0.15
	// 	const cpx = cx() * beta + (src.x + end.x) / 2 * ( 1 - beta);
	// 	const cpy = cy() * beta + (src.y + end.y) / 2 * ( 1 - beta);
	// 	return `M ${src.x},${src.y} Q ${cpx},${cpy} ${end.x},${end.y}`;
	// 	// return `M ${d.source.x},${d.source.y} A ${dr},${dr} 0 0 1 ${end.x},${end.y}`;
	// }
	const bundleLine = d3
		.line<[number, number]>()
		.x((p) => p[0])
		.y((p) => p[1])
		.curve(d3.curveBundle.beta(0.88)); // beta is how aggressively edges bundle
		
	function bundledPath(d: any): string {
		const src = d.source;
		const end =
			d.type === 'TFL' && $aesSettings.TF === 'endShape'
			? trimPath(src, d.target, 10)
			: { x: d.target.x, y: d.target.y };

		const tgt = { x: end.x, y: end.y };
		const srcRi = ringIndexOf(src);
		const tgtRi = ringIndexOf(d.target);

		let points: [number, number][];

		const srcAngle = Math.atan2(src.y - cy(), src.x - cx());
		const tgtAngle = Math.atan2(d.target.y - cy(), d.target.x - cx());
		// midpoint radius: halfway between the two rings
		const rMid = (ringRadii[srcRi] + ringRadii[tgtRi]) / 2;
		// control point 1: at source angle, mid radius
		const cp1 = {
		x: cx() + rMid * Math.cos(srcAngle),
		y: cy() + rMid * Math.sin(srcAngle),
		};
		// control point 2: at target angle, mid radius
		const cp2 = {
		x: cx() + rMid * Math.cos(tgtAngle),
		y: cy() + rMid * Math.sin(tgtAngle),
		};
		points = [
		[src.x, src.y],
		[cp1.x, cp1.y],
		[cp2.x, cp2.y],
		[tgt.x, tgt.y],
		];
		return bundleLine(points) ?? '';
	}

	let prevGroupNodes: boolean | undefined = undefined;
	let prevNetworkData: typeof networkData | undefined = undefined;
	let prevCT: boolean | undefined = undefined;
	let prevLR: string | undefined = undefined;
	let prevTF: string | undefined = undefined;

	$: {
		const groupChanged = $aesSettings.groupNodes !== prevGroupNodes;
		const dataChanged  = networkData !== prevNetworkData;

		if (groupChanged || dataChanged) {
			prevGroupNodes   = $aesSettings.groupNodes;
			prevNetworkData  = networkData;
			// also sync style trackers so their $: blocks don't fire after render
			prevCT = $aesSettings.CT;
			prevLR = $aesSettings.LR;
			prevTF = $aesSettings.TF;
			if (svgContainer && containerDiv) renderNetwork();
		}
	}

	$: {
		const ct = $aesSettings.CT;
		if (ct !== prevCT && nodeSelection) {
			prevCT = ct;
			updateNodeColors(nodeSelection, $colorScale, $aesSettings);
		}
	}

	$: {
		const lr = $aesSettings.LR;
		const tf = $aesSettings.TF;
		if ((lr !== prevLR || tf !== prevTF) && linkSelection) {
			prevLR = lr;
			prevTF = tf;
			updateEdgesAes(linkSelection, $aesSettings);
		}
	}

	$: applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	$: applyCycleHighlight($highlightedCycle, nodeSelection, linkSelection);

	const renderNetwork = () => {
		if (!svgContainer || !containerDiv) return;
		if (!networkData?.nodes?.length) return;
		simulation?.stop();
		
		_W = containerDiv.clientWidth || 600;
 		_H = containerDiv.clientHeight || 500;
		
		const n = $sender === $receiver ? 3 : ringCount();
		
		if (ringRadii.length !== n) {
			const minDim = Math.min(_W, _H);
			const step = (minDim * 0.48) / n;           // outermost ring ≈ 48% of shortest side
			ringRadii = Array.from({ length: n }, (_, i) => minDim * 0.08 + i * step);
			ringRotations = new Array(n).fill(0);
			nodeBaseAngle.clear();
		}

		const safeNodes = networkData.nodes.map((d) => ({ ...d, x: undefined, y: undefined }));
		const safeLinks = networkData.links.map((l) => ({
			...l,
			source: typeof l.source === 'object' ? l.source.id : l.source,
			target: typeof l.target === 'object' ? l.target.id : l.target,
		}));

		const { nodes: rawNodes, links: rawLinks } = $aesSettings.groupNodes
			? deduplicateTFs(safeNodes, safeLinks)
			: { nodes: safeNodes, links: safeLinks };

		const nodes = rawNodes.map((d: any) => ({ ...d }));
		const links = rawLinks.map((d: any) => ({ ...d }));

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
		
		const nodeById = new Map(nodes.map((n) => [n.id, n]));
		const simLinks = links.map((l: any) => ({
			...l,
			source: nodeById.get(typeof l.source === 'object' ? l.source.id : l.source) ?? l.source,
			target: nodeById.get(typeof l.target === 'object' ? l.target.id : l.target) ?? l.target,
		}));

		const svg = d3.select(svgContainer);
		d3.select(svgContainer).selectAll('g').remove();
		d3.select(svgContainer).selectAll('path').remove();

		svg
			.attr('viewBox', [0, 0, _W, _H])
			.style('background', 'transparent')
			.style('cursor', 'grab');

		const zoomLayer = svg.append('g');
		const zoom = d3.zoom<SVGSVGElement, unknown>().on('zoom', (event) => {zoomLayer.attr('transform', event.transform)});
		svg.call(zoom as any);
		svg.call(zoom.transform, d3.zoomIdentity.translate( _W / 7, _H / 8).scale(0.9))

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
				.attr('stroke-width', 1.5)
				.attr('r', (i) => ringRadii[i]);
		}
		syncCircles();

		simulation = d3
			.forceSimulation(nodes)
			.force('link', d3
					.forceLink(simLinks)
					.id((d: any) => d.id)
					.strength(0.1)
			)
			.force('charge', d3.forceManyBody().strength(-23))
			.force('collide', d3.forceCollide((d: any) => 10))
			.force('center', d3.forceCenter(cx(), cy()));

		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke-width', 1)
			.selectAll('path')
			.data(simLinks)
			.join('path')
			.attr('stroke-opacity', (d: any) => (d.type === 'LR' ? 0.9 : 0.6))
			.attr('mix-blend-mode', 'multiply') // for edges overlaps
			.call((selection) => aesEdge(selection, $aesSettings.LR,$aesSettings.TF));


		const node = zoomLayer
			.append('g')
			.attr('stroke-width', 1)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('stroke', (d: any) => ( ($aesSettings.groupNodes && d._mergedCount > 1) ? '#000' : '#fff') )
			.call((sel) => drawNode(sel, $colorScale, $aesSettings.CT))
			.on('click', (event: any, d: { id: string; name: string, _mergedCount: number }) => {
				if (d._mergedCount > 1) return;
				selectedNode.set(d.id);
				selectedNodeName.set(d.name);
				highlightNode(d.id, simLinks, node, link);
			});

		svg.on('click', (event) => {
			if (event.target === svg.node()) {
				node.attr('opacity', 1);
				link.attr('opacity', 1);
				resetNodesSize(nodeSelection);
			}
		});

		node.append('title').text((d: any) => {
			if (d._mergedNames?.length > 1) {
				return `Merged TFs (${d._mergedCount}):\n${d._mergedNames.join('\n')}\n(${d.celltype})`;
			}
			return `${d.name}\n(${d.celltype})\n${d.moltype}\nB.: ${d.betweenness.toFixed(4)}\nP.: ${d.pagerank.toFixed(4)}`;
		});
		link.append('title')
			.text((d: any) =>
				d.type === 'LR'
					? `LR (${d.source.name} → ${d.target.name}) weight: ${d.weight.toFixed(4)} significance: ${d.significance.toFixed(4)}`
					: `${d.type} (${d.source.name} → ${d.target.name})`
			);

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
			link.attr('d', bundledPath);
		});

		function reprojectRing(ri: number) {
			nodes.forEach((d) => {
				if (ringIndexOf(d) === ri) projectNode(d);
			});
			node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
			link.attr('d', bundledPath);
		}

		const handleLayer = zoomLayer.append('g').attr('class', 'ring-handles');
		const ringGs = handleLayer
			.selectAll<SVGGElement, number>('g.ring-g')
			.data(d3.range(n))
			.join('g')
			.attr('class', 'ring-g');

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
		nodeSelection = node;
		linkSelection = link;

		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	};

	onMount(() => { requestAnimationFrame(() => renderNetwork()); });
	onDestroy(() => { simulation?.stop(); });
</script>
<div style="position: relative; width: 100%; height: 100%;">
	<DrawNetLegend />
	<div bind:this={containerDiv} style="width: 100%; height: 100%;">
	<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
	</div>
</div>
