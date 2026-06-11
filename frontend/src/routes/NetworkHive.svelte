<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		drawNode,
		highlightNode,
		aesEdge,
		trimPath,
		applyHighlightSearch,
		resetNodesSize,
		deduplicateTFs,
		applyCycleHighlight,
		updateEdgesAes,
		updateNodeColors
	} from './utils';
	import {
		colorScale,
		selectedNode,
		selectedNodeName,
		highlightedNode,
		aesSettings,
		highlightedCycle,
		selectedComparison,
		sender,
		receiver
	} from '$lib/stores';
	import DrawNetLegend from './drawNetLegend.svelte';
	import { toSvg, toPng } from 'html-to-image';

	export let networkData: { nodes: any[]; links: any[] };
	let exportContainer: HTMLDivElement;

	async function handleDownload(format: 'svg' | 'png') {
		if (!exportContainer) return;

		const opts = {
			backgroundColor: 'white',
			cacheBust: true,
			pixelRatio: 2,
			filter: (node: Node) => {
				if (node instanceof HTMLElement && node.classList?.contains('no-export')) return false;
				return true;
			}
		};

		const baseName = `${$selectedComparison}_${$sender}_${$receiver}_NetworkHive`;

		const dataUrl = format === 'svg'
			? await toSvg(exportContainer, opts)
			: await toPng(exportContainer, opts);

		const a = document.createElement('a');
		a.href = dataUrl;
		a.download = `${baseName}.${format}`;
		a.click();
	}

	export async function expdownloadSVG() {
		await handleDownload('svg');
	}

	export async function expdownloadPNG() {
		await handleDownload('png');
	}
	let svgContainer: SVGSVGElement;
	let containerDiv: HTMLDivElement;

	let nodeSelection: any = null;
	let linkSelection: any = null;

	let _W = 600;
	let _H = 500;
	const cx = () => _W / 2;
	const cy = () => _H / 2;

	const MOLTYPES = ['TF', 'ligand', 'receptor'] as const;
	type Moltype = (typeof MOLTYPES)[number];

	const axisAngle = new Map<Moltype, number>([
		['TF', -Math.PI / 2],
		['ligand', -Math.PI / 2 + (2 * Math.PI) / 3],
		['receptor', -Math.PI / 2 + (4 * Math.PI) / 3]
	]);

	const AXIS_MIN = 25; // inner dead-zone
	const AXIS_MAX_FRAC = 0.8; // fraction of min(W,H) for the outer end

	function axisLength(): number {
		return Math.min(_W, _H) * AXIS_MAX_FRAC;
	}

	let prevGroupNodes: boolean | undefined = undefined;
	let prevNetworkData: typeof networkData | undefined = undefined;
	let prevCT: boolean | undefined = undefined;
	let prevLR: string | undefined = undefined;
	let prevTF: string | undefined = undefined;

	$: {
		const groupChanged = $aesSettings.groupNodes !== prevGroupNodes;
		const dataChanged = networkData !== prevNetworkData;
		if (groupChanged || dataChanged) {
			prevGroupNodes = $aesSettings.groupNodes;
			prevNetworkData = networkData;
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
	$: applyCycleHighlight(
		$highlightedCycle,
		nodeSelection,
		linkSelection,
		$colorScale,
		$aesSettings
	);

	// Place node at distance `r` along its axis
	function projectNode(node: any) {
		const angle = axisAngle.get(node.moltype as Moltype) ?? 0;
		node.x = cx() + Math.cos(angle) * node._r;
		node.y = cy() + Math.sin(angle) * node._r;
	}

	// Curved link path: cubic Bézier that bends around the centre
	function hivePath(d: any): string {
		const src = d.source;
		const tgt =
			d.type === 'TFL' && $aesSettings.TF === 'endShape'
				? trimPath(d.source, d.target, 17)
				: { x: d.target.x, y: d.target.y };

		const beta = -0.18;
		const cp1x = cx() * beta + src.x * (1 - beta);
		const cp1y = cy() * beta + src.y * (1 - beta);
		const cp2x = cx() * beta + tgt.x * (1 - beta);
		const cp2y = cy() * beta + tgt.y * (1 - beta);

		return `M ${src.x},${src.y} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${tgt.x},${tgt.y}`;
	}

	const renderNetwork = () => {
		if (!svgContainer || !containerDiv) return;
		if (!networkData?.nodes?.length) return;

		_W = containerDiv.clientWidth || 600;
		_H = containerDiv.clientHeight || 500;

		const safeNodes = networkData.nodes.map((d) => ({
			...d,
			x: undefined,
			y: undefined,
			fx: undefined,
			fy: undefined
		}));
		const safeLinks = networkData.links.map((l) => ({
			...l,
			source: typeof l.source === 'object' ? l.source.id : l.source,
			target: typeof l.target === 'object' ? l.target.id : l.target
		}));

		const { nodes: rawNodes, links: rawLinks } = $aesSettings.groupNodes
			? deduplicateTFs(safeNodes, safeLinks)
			: { nodes: safeNodes, links: safeLinks };

		const nodes: any[] = rawNodes.map((d: any) => ({ ...d }));
		const links: any[] = rawLinks.map((d: any) => ({ ...d }));

		// Distribute nodes along their axis.  If a node already has `_r` from a
		// previous render we reuse it (stable drag position across re-renders).
		const perAxis = new Map<Moltype, number>([
			['TF', 0],
			['ligand', 0],
			['receptor', 0]
		]);
		nodes.forEach((n) => {
			const mt = n.moltype as Moltype;
			if (!MOLTYPES.includes(mt)) return;
			if (n._r === undefined) {
				const idx = perAxis.get(mt) ?? 0;
				const step =
					(axisLength() - AXIS_MIN) / Math.max(1, nodes.filter((x) => x.moltype === mt).length);
				n._r = AXIS_MIN + idx * step + step * 0.5;
				perAxis.set(mt, idx + 1);
			}
			projectNode(n);
		});

		const nodeById = new Map(nodes.map((n) => [n.id, n]));
		const simLinks = links.map((l: any) => ({
			...l,
			source: nodeById.get(typeof l.source === 'object' ? l.source.id : l.source) ?? l.source,
			target: nodeById.get(typeof l.target === 'object' ? l.target.id : l.target) ?? l.target
		}));

		d3.select(svgContainer).selectAll('*').remove();
		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, _W, _H])
			.style('background', 'transparent')
			.style('cursor', 'grab');
		const zoomLayer = svg.append('g');
		const zoom = d3.zoom<SVGSVGElement, unknown>().on('zoom', (event) => {
			zoomLayer.attr('transform', event.transform);
		});
		svg.call(zoom as any);
		svg.call(
			zoom.transform,
			d3.zoomIdentity
				.translate(_W / 2, _H / 2)
				.scale(0.9)
				.translate(-cx(), -cy())
		);

		// draw axes
		const axisGroup = zoomLayer.append('g').attr('class', 'hive-axes');
		MOLTYPES.forEach((mt) => {
			const angle = axisAngle.get(mt) ?? 0;
			const len = axisLength();
			const x2 = cx() + Math.cos(angle) * len;
			const y2 = cy() + Math.sin(angle) * len;

			axisGroup
				.append('line')
				.attr('x1', cx())
				.attr('y1', cy())
				.attr('x2', x2)
				.attr('y2', y2)
				.attr('stroke', '#ababab')
				.attr('stroke-dasharray', '4 4')
				.attr('stroke-width', 1.5);

			axisGroup
				.append('text')
				.attr('x', cx() + Math.cos(angle) * (len + 18))
				.attr('y', cy() + Math.sin(angle) * (len + 18))
				.attr('fill', '#6b7280')
				.attr('font-size', 12)
				.attr('font-family', 'sans-serif')
				.attr('text-anchor', 'middle')
				.attr('dominant-baseline', 'central')
				.text(mt);
		});

		// a small dot at centre
		axisGroup
			.append('circle')
			.attr('cx', cx())
			.attr('cy', cy())
			.attr('r', 4)
			.attr('fill', '#ababab');

		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke-width', 1)
			.selectAll('path')
			.data(simLinks)
			.join('path')
			.attr('stroke-opacity', (d: any) => (d.type === 'LR' ? 0.85 : 0.55))
			.call((sel) => aesEdge(sel, $aesSettings.LR, $aesSettings.TF))
			.attr('d', hivePath);

		const node = zoomLayer
			.append('g')
			.attr('stroke-width', 1)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('stroke', (d: any) => ($aesSettings.groupNodes && d._mergedCount > 1 ? '#000' : '#fff'))
			.call((sel) => drawNode(sel, $colorScale, $aesSettings.CT))
			.attr('transform', (d: any) => `translate(${d.x ?? cx()},${d.y ?? cy()})`)
			.on('click', (event: any, d: { id: string; name: string; _mergedCount: number }) => {
				if (d._mergedCount > 1) return;
				selectedNode.set(d.id);
				selectedNodeName.set(d.name);
				highlightNode(d.id, simLinks, node, link);
			});

		svg.on('click', (event) => {
			if (event.target === svg.node()) {
				highlightNode(null, simLinks, node, link);
				resetNodesSize(nodeSelection);
			}
		});

		// Node drag along axis
		node.call(
			d3
				.drag<any, any>()
				.on('start', function (_ev, d) {
					d3.select(this).raise();
				})
				.on('drag', function (ev, d: any) {
					const mt = d.moltype as Moltype;
					if (!MOLTYPES.includes(mt)) return;
					const angle = axisAngle.get(mt) ?? 0;
					// Project onto the axis vector
					const dx = ev.x - cx();
					const dy = ev.y - cy();
					const dot = dx * Math.cos(angle) + dy * Math.sin(angle);
					d._r = Math.max(AXIS_MIN, Math.min(axisLength(), dot));
					projectNode(d);
					d3.select(this).attr('transform', `translate(${d.x},${d.y})`);
					link.attr('d', hivePath);
				})
			// no drag-end needed, position remains in d._r
		);

		node.append('title').text((d: any) => {
			if (d._mergedNames?.length > 1) {
				return `Merged TFs (${d._mergedCount}):\n${d._mergedNames.join('\n')}\n(${d.celltype})`;
			}
			return `${d.name}\n(${d.celltype})\n${d.moltype}\nB.: ${d.betweenness?.toFixed(4) ?? 'n/a'}\nP.: ${d.pagerank?.toFixed(4) ?? 'n/a'}`;
		});
		link
			.append('title')
			.text((d: any) =>
				d.type === 'LR'
					? `LR (${d.source.name} → ${d.target.name}) weight: ${d.weight?.toFixed(4)} significance: ${d.significance?.toFixed(4)}`
					: `${d.type} (${d.source.name} → ${d.target.name})`
			);

		nodeSelection = node;
		linkSelection = link;

		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	};

	onMount(() => {
		requestAnimationFrame(() => renderNetwork());
	});
</script>

<div bind:this={exportContainer} style="position: relative; width: 100%; height: 100%;">
	<DrawNetLegend />
	<div bind:this={containerDiv} style="width: 100%; height: 100%;">
		<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
	</div>
</div>
