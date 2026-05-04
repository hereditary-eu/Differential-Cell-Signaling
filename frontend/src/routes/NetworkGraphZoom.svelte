<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		zoomBehavior,
		drawNode,
		highlightNode,
		aesEdge,
		trimPath,
		defineMarkers,
		applyHighlightSearch,
		resetNodesSize,
		deduplicateTFs
	} from './utils';
	import {
		colorScale,
		selectedNode,
		selectedNodeName,
		highlightedNode,
		aesSettings
	} from '$lib/stores';
	import DrawNetLegend from './drawNetLegend.svelte';

	export let networkData: { nodes: any[]; links: any[] };

	let svgContainer: SVGSVGElement;
	let containerDiv: HTMLDivElement;          
	let simulation: d3.Simulation<any, undefined>;

	let nodeSelection: any = null;
	let linkSelection: any = null;

	function renderNetwork() {
		if (!svgContainer || !containerDiv) return;
		if (!networkData?.nodes?.length) return;
		simulation?.stop();

		const W = containerDiv.clientWidth  || 600;   
		const H = containerDiv.clientHeight || 500;

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
		const nodeById = new Map(nodes.map((n) => [n.id, n]));
		const simLinks = links.map((l: any) => ({
			...l,
			source: nodeById.get(typeof l.source === 'object' ? l.source.id : l.source) ?? l.source,
			target: nodeById.get(typeof l.target === 'object' ? l.target.id : l.target) ?? l.target,
		}));

		d3.select(svgContainer).selectAll('*').remove();
		const svg = d3
			.select(svgContainer)
			.attr('viewBox', [0, 0, W, H])             
			.style('background', 'transparent')
			.style('cursor', 'grab');

		defineMarkers(svg);

		const zoomLayer = svg.append('g');
		const { zoom } = zoomBehavior(zoomLayer);      
		svg.call(zoom as any);
		svg.call(zoom.transform as any, d3.zoomIdentity); 
		simulation = d3
			.forceSimulation(nodes)
			.force('link', d3
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
			link.attr('d', (d: any) => {
				let end = { x: d.target.x, y: d.target.y };
				if (d.type === 'TFL' && $aesSettings.TF === 'endShape') {
					end = trimPath(d.source, d.target, 10);
				}
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy);
				return `M ${d.source.x},${d.source.y} A ${dr},${dr} 0 0 1 ${end.x},${end.y}`;
			});
			node.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
		});

		applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);
	}

	$: {
		$aesSettings;
		if (networkData?.nodes?.length) renderNetwork();
	}

	$: applyHighlightSearch($highlightedNode, nodeSelection, linkSelection, networkData);

	onMount(() => {
		requestAnimationFrame(() => renderNetwork());   // containerDiv has real size
	});
	onDestroy(() => {
		simulation?.stop();
	});
</script>

<div style="position: relative; width: 100%; height: 100%;">
	<DrawNetLegend />
	<div bind:this={containerDiv} style="width: 100%; height: 100%;">
		<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
	</div>
</div>