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

		const baseName = `${$selectedComparison}_${$sender}_${$receiver}_NetworkClassic`;

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
	let simulation: d3.Simulation<any, undefined>;

	let nodeSelection: any = null;
	let linkSelection: any = null;

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
	$: applyCycleHighlight(
		$highlightedCycle,
		nodeSelection,
		linkSelection,
		$colorScale,
		$aesSettings
	);

	const bundleLine = d3
		.line<[number, number]>()
		.x((p) => p[0])
		.y((p) => p[1])
		.curve(d3.curveBundle.beta(0.88)); // beta is how aggressively edges bundle

	function renderNetwork() {
		if (!svgContainer || !containerDiv) return;
		if (!networkData?.nodes?.length) return;
		simulation?.stop();

		const W = containerDiv.clientWidth || 600;
		const H = containerDiv.clientHeight || 500;

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

		const nodes = rawNodes.map((d: any) => ({ ...d }));
		const links = rawLinks.map((d: any) => ({ ...d }));
		const nodeById = new Map(nodes.map((n: any) => [n.id, n]));
		const simLinks = links.map((l: any) => ({
			...l,
			source: nodeById.get(typeof l.source === 'object' ? l.source.id : l.source) ?? l.source,
			target: nodeById.get(typeof l.target === 'object' ? l.target.id : l.target) ?? l.target
		}));

		d3.select(svgContainer).selectAll('*').remove();

		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, W, H])
			.style('background', 'transparent')
			.style('cursor', 'grab');

		const zoomLayer = svg.append('g');
		const zoom = d3.zoom<SVGSVGElement, unknown>().on('zoom', (event) => {
			zoomLayer.attr('transform', event.transform);
		});
		svg.call(zoom as any);
		svg.call(zoom.transform, d3.zoomIdentity.translate(W / 3, H / 3).scale(0.5));

		simulation = d3
			.forceSimulation(nodes)
			.force(
				'link',
				d3
					.forceLink(simLinks)
					.id((d: any) => d.id)
					.distance(15)
					.strength(0.1)
			)
			.force('charge', d3.forceManyBody().strength(-23))
			.force('center', d3.forceCenter(W / 2, H / 2));

		const link = zoomLayer
			.append('g')
			.attr('fill', 'none')
			.attr('stroke-opacity', 0.9)
			.attr('stroke-width', 1)
			.selectAll('path')
			.data(simLinks)
			.join('path')
			.call((sel) => aesEdge(sel, $aesSettings.LR, $aesSettings.TF));

		const node = zoomLayer
			.append('g')
			.attr('stroke-width', 1)
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('stroke', (d: any) => ($aesSettings.groupNodes && d._mergedCount > 1 ? '#000' : '#fff'))
			.call((sel) => drawNode(sel, $colorScale, $aesSettings.CT))
			.on('click', (event: any, d: { id: string; name: string; _mergedCount: number }) => {
				if (d._mergedCount > 1) return;
				selectedNode.set(d.id);
				selectedNodeName.set(d.name);
				highlightNode(d.id, simLinks, node, link);
			});

		node.call(
			d3.drag<any, any>().on('drag', (e, d) => {
				d.fx = e.x;
				d.fy = e.y;
			})
		);

		nodeSelection = node;
		linkSelection = link;

		svg.on('click', (event) => {
			if (event.target === svg.node()) {
				// selectedNode.set('');
				// selectedNodeName.set('');
				highlightNode(null, simLinks, node, link);
				resetNodesSize(nodeSelection);
			}
		});

		node.append('title').text((d: any) => {
			if (d._mergedNames?.length > 1) {
				return `Merged TFs (${d._mergedCount}):\n${d._mergedNames.join('\n')}\n(${d.celltype})`;
			}
			return `${d.name}\n(${d.celltype})\n${d.moltype}\nB.: ${d.betweenness?.toFixed(4)}\nP.: ${d.pagerank?.toFixed(4)}`;
		});
		link
			.append('title')
			.text((d: any) =>
				d.type === 'LR'
					? `LR (${d.source.name} → ${d.target.name}) weight: ${d.weight.toFixed(4)} significance: ${d.significance.toFixed(4)}`
					: `${d.type} (${d.source.name} → ${d.target.name})`
			);

		simulation.on('tick', () => {
			link.attr('d', (d: any) => {
				let endX = d.target.x;
				let endY = d.target.y;
				if (d.type === 'TFL' && $aesSettings.TF === 'endShape') {
					const trimmed = trimPath(d.source, d.target, 14);
					endX = trimmed.x;
					endY = trimmed.y;
				}
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy);
				return `M ${d.source.x},${d.source.y} A ${dr},${dr} 0 0 1 ${endX},${endY}`;
			});
			node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
		});

		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	}

	onMount(() => {
		requestAnimationFrame(() => renderNetwork());
	});
	onDestroy(() => {
		simulation?.stop();
	});
</script>

<div bind:this={exportContainer} style="position: relative; width: 100%; height: 100%;">
	<DrawNetLegend />
	<div bind:this={containerDiv} style="width: 100%; height: 100%;">
		<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
	</div>
</div>
