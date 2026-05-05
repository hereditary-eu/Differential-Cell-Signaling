<script lang="ts">
	import * as d3 from 'd3';
	import {
		sender,
		receiver,
		colorScale,
		reverseSig,
		selectedNode,
		selectedNodeName,
		neighborhoodData,
		filteringQueryStr
	} from '$lib/stores';
	import { aesEdge, drawNode, defineMarkers, trimPath, deduplicateTFs } from './utils';
	import GroupToggle from './GroupToggle.svelte';

	let groupNodes = $state(true);
	let isHorizontal = $state(true);
	let maxSteps = $state(4);

	const backend = import.meta.env.VITE_BACKEND_URL;

	// update selectedNode and pass neighboorhoodData to detailed view
	$effect(() => {
		if ($selectedNode) {
			fetchNeighborhood($selectedNode);
		}
	});
	async function fetchNeighborhood(nodeId: string) {
		if (!$sender || !$receiver) return;
		try {
			const res = await fetch(
				`${backend}/api/neighborhood?root_id=${nodeId}&max_steps=${maxSteps}&${$filteringQueryStr}`
			);
			const data = await res.json();
			neighborhoodData.set(data);
			console.log($neighborhoodData);
		} catch (err) {
			console.error('Error fetching neighborhood data:', err);
		}
	}

	let svgContainer: SVGSVGElement;
	let containerDiv: HTMLDivElement;

	function getYRank(d: any): number {
		const ct = d.celltype;
		const mt = d.moltype ?? '';
		const isSender = ct === $sender;
		const isReceiver = ct === $receiver;
		if (isSender && mt === 'TF') return 0;
		if (isSender && mt === 'ligand') return 1;
		if (isReceiver && mt === 'receptor') return 2;
		if (isReceiver && mt === 'TF') return 3;
		if (isReceiver && mt === 'ligand') return 4;
		if (isSender && mt === 'receptor') return 5;
		return 1.5;
	}

	function renderTree() {
		if (!$neighborhoodData?.nodes?.length || !$neighborhoodData?.rootId) return;
		if ($neighborhoodData?.nodes?.length <= 1) {
			d3.select(svgContainer).selectAll('*').remove();
			d3.select(svgContainer).text('Searched node not found in current sender-receiver sub-graph.').attr('fill', '#000');
			return;
		};

		const W = containerDiv?.clientWidth || 600;
		const H = containerDiv?.clientHeight || 500;

		const PADDING = 20;
		const numRanks = $reverseSig ? 4 : 6;
		
		const rankToFixed = (rank: number) =>
			isHorizontal
			? PADDING + (rank / (numRanks-1)) * (W - PADDING * 1.5 )
			: PADDING + (rank / (numRanks-1)) * (H - PADDING * 1.5 );
		
		const { nodes: dedupNodes, links: dedupLinks } = groupNodes
	  		? deduplicateTFs($neighborhoodData.nodes, $neighborhoodData.links)
  			: { nodes: $neighborhoodData.nodes, links: $neighborhoodData.links };

		// Attach fixed direction
		const nodes = dedupNodes.map((d) => {
			const rank = getYRank(d);
			return isHorizontal
				? {...d, fx: rankToFixed(getYRank(d))}
				: {...d, fy: rankToFixed(getYRank(d))}
			
		});
		const links = dedupLinks.map((d) => ({ ...d }));

		d3.select(svgContainer).selectAll('*').remove();

		const svg = d3
			.select(svgContainer)
			.attr('viewBox', `0 0 ${W} ${H}`)
			.style('background', 'transparent')
			.style('cursor', 'grab');

		defineMarkers(svg);

		const zoomLayer = svg.append('g');
		const zoom = d3
			.zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.1, 20])
			.on('zoom', (event) => zoomLayer.attr('transform', event.transform));

		svg.call(zoom as any);

		const nodeById = new Map(nodes.map((n) => [n.id, n]));
		const simLinks = links.map((l) => ({
			...l,
			source: nodeById.get(l.source) ?? l.source,
			target: nodeById.get(l.target) ?? l.target
		}));

		const simulation = d3
			.forceSimulation(nodes)
			.force('link', d3.forceLink(simLinks).id((d: any) => d.id) )
			.force('charge', d3.forceManyBody().strength(-80).distanceMax(50))
			.force('x', isHorizontal ? d3.forceX(W / 2).strength(0) : d3.forceX(W / 2).strength(0.1))
			.force('y', isHorizontal ? d3.forceY(H / 2).strength(0.1) : null as any)
			.force('collide', d3.forceCollide(15));

		const linkSel = zoomLayer
			.append('g')
			.selectAll('line')
			.data(simLinks)
			.join('line')
			.attr('fill', 'none')
			.call((sel) => aesEdge(sel, 'volcano', 'endShape'));

		const nodeSel = zoomLayer
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('stroke', (d: any) => (d._mergedCount > 1 ? '#000000' : '#fff'))
			.attr('stroke-width', 1)
			.call((sel) => drawNode(sel, $colorScale, true))
			.on('click', (event: any, d: { id: string; name: string; _mergedCount: number }) => {
				if (d._mergedCount > 1) return;
				selectedNode.set(d.id);
				selectedNodeName.set(d.name);
			});

		nodeSel
			.append('text')
			.attr('text-anchor', isHorizontal ? 'end' : 'middle')
			.attr('dx', isHorizontal ? '-0.8em' : '0em')
			.attr('dy', isHorizontal ? '-0.4em' : '2em') 
			.attr('font-size', '9px')
			.attr('color', '#000000')
			.attr('stroke', '#000000')
			.attr('stroke-width', 0.5)
			.attr('pointer-events', 'none')
			.text((d: any) => {
				if (d._mergedCount > 1) return `${d._mergedCount} TFs`;
				const name = d.name ?? '';
				return name;
			});

		nodeSel.append('title').text((d: any) => {
			if (d._mergedNames?.length > 1) {
				return `Merged TFs (${d._mergedCount}):\n${d._mergedNames.join('\n')}\n(${d.celltype})`;
			}
			return `${d.name}\n(${d.celltype})\n${d.moltype}`;
		});

		nodeSel.call(
			d3
				.drag<any, any>()
				.on('start', (e, d) => {
					if (isHorizontal) d.fy = d.y;
					else d.fx = d.x;
				})
				.on('drag', (e, d) => {
					if (isHorizontal) d.fy = e.y;
					else d.fx = e.x;
				})
				.on('end', (e, d) => {
					if (isHorizontal) d.fy = null;
					else d.fx = null;
				})
		);

		nodeSel
			.on('mouseover', (_e, d: any) => {
				const neighborIds = new Set<number>();
				simLinks.forEach((l: any) => {
					if (l.source.id === d.id) neighborIds.add(l.target.id);
					if (l.target.id === d.id) neighborIds.add(l.source.id);
				});
				linkSel.attr('stroke-opacity', (l: any) =>
					l.source.id === d.id || l.target.id === d.id ? 1 : 0.06
				);
				nodeSel.attr('opacity', (n: any) => (n.id === d.id || neighborIds.has(n.id) ? 1 : 0.15));
			})
			.on('mouseout', () => {
				linkSel.attr('stroke-opacity', 0.9);
				nodeSel.attr('opacity', 1);
			});

		simulation.on('tick', () => {
			linkSel
				.attr('x1', (d: any) => d.source.x)
				.attr('y1', (d: any) => d.source.y)
				.attr('x2', (d: any) => d.target.x)
				.attr('y2', (d: any) => d.target.y)
				.attr('d', (d: any) => {
					let end = { x: d.target.x, y: d.target.y };
					if (d.type === 'TFL') {
						console.log('gonna trim em all')
						end = trimPath(d.source, d.target, 60); // this is evaluated but does not work...
					}
					const dx = d.target.x - d.source.x;
					const dy = d.target.y - d.source.y;
					const dr = Math.sqrt(dx * dx + dy * dy); // radius for arc
					return `
					M ${d.source.x},${d.source.y}
					A ${dr},${dr} 0 0 1 ${end.x},${end.y}
				`;
				});
			nodeSel.attr('transform', (d: any) => `translate(${d.x ?? 0},${d.y ?? 0})`);
		});

		simulation.on('end', () => {
			const gNode = zoomLayer.node() as SVGGElement;
			if (!gNode) return;
			const box = gNode.getBBox();
			if (!box.width || !box.height) return;
			const scale = 0.85 * Math.min(W / box.width, H / box.height);
			const tx = W / 2 - scale * (box.x + box.width / 2);
			const ty = H / 2 - scale * (box.y + box.height / 2);
			svg.call(zoom.transform as any, d3.zoomIdentity.translate(tx, ty).scale(scale));
		});
	}

	$effect(() => { if ($neighborhoodData || maxSteps || groupNodes !== undefined) renderTree(); });
</script>

<div style="position: relative; width: 100%; height: 100%; display: flex; flex-direction: column; overflow: hidden;">
	<div style="
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
		padding: 4px 8px;
		flex-shrink: 0;
		border-bottom: 1px solid #e5e5e5;
		background: white;
		z-index: 10;
	">
		<label for="input-maxSteps" style="font-size: 11px; margin: 0; white-space: nowrap;">max steps:</label>
		<input
			id="input-maxSteps"
			type="number"
			bind:value={maxSteps}
			min="1"
			max="5"
			style="
				width: 52px;
				padding: 2px 6px;
				font-size: 11px;
				border: 1px solid #ccc;
				border-radius: 4px;
			"
		/>
		<button
			onclick={() => { isHorizontal = !isHorizontal; }}
			style="
				padding: 2px 8px;
				font-size: 11px;
				border: 1px solid #ccc;
				border-radius: 4px;
				background: white;
				cursor: pointer;
				display: flex;
				align-items: center;
				gap: 4px;
			"
			title="Toggle layout orientation"
		>
			{#if isHorizontal}
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
					<line x1="7" y1="1" x2="7" y2="13"/>
					<line x1="3" y1="4" x2="7" y2="1"/><line x1="11" y1="4" x2="7" y2="1"/>
				</svg>
				Vertical
			{:else}
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
					<line x1="1" y1="7" x2="13" y2="7"/>
					<line x1="10" y1="3" x2="13" y2="7"/><line x1="10" y1="11" x2="13" y2="7"/>
				</svg>
				Horizontal
			{/if}
		</button>
		<GroupToggle bind:checked={groupNodes} label="Group TFs" />

	</div>
	<div bind:this={containerDiv} style="flex: 1; min-height: 0; width: 100%;">
		<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
	</div>
</div>