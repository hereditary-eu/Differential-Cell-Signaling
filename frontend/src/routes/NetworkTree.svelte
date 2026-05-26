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
		filteringQueryStr,
		selectedComparison
	} from '$lib/stores';
	import { aesEdge, drawNode, trimPath, deduplicateTFs } from './utils';
	import GroupToggle from './GroupToggle.svelte';
	import { downloadSVG } from './downloadSVG';
	import { barycentreSort } from './barycenterSortNodes';

	let groupNodes = $state(true);
	let isHorizontal = $state(true);
	let maxSteps = $state(4);

	const backend = import.meta.env.VITE_BACKEND_URL ?? '';

	function handleDownloadSVG() {
		downloadSVG(
			svgContainer,
			`${$selectedComparison}_${$selectedNodeName}_Neighborhood_${maxSteps}steps_${$sender}_${$receiver}.svg`
		);
	}

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
		} catch (err) {
			console.error('Error fetching neighborhood data:', err);
		}
	}

	// svelte-ignore non_reactive_update
	let svgContainer: SVGSVGElement;
	// svelte-ignore non_reactive_update
	let containerDiv: HTMLDivElement;

	// Rank definitions – canonical order, root rank rotated to position 0
	type RankDef = { celltype: string; moltype: string; label: string };

	function buildAllRankDefs(rootNode: any): RankDef[] {
		const s = $sender ?? '';
		const r = $receiver ?? '';
		const full: RankDef[] = $reverseSig
			? [
					{ celltype: s, moltype: 'TF',       label: `${s}\nTF` },
					{ celltype: s, moltype: 'ligand',   label: `${s}\nLigand` },
					{ celltype: r, moltype: 'receptor', label: `${r}\nReceptor` },
					{ celltype: r, moltype: 'TF',       label: `${r}\nTF` },
					{ celltype: r, moltype: 'ligand',   label: `${r}\nLigand` },
					{ celltype: s, moltype: 'receptor', label: `${s}\nReceptor` }
				]
			: [
					{ celltype: s, moltype: 'TF',       label: `${s}\nTF` },
					{ celltype: s, moltype: 'ligand',   label: `${s}\nLigand` },
					{ celltype: r, moltype: 'receptor', label: `${r}\nReceptor` },
					{ celltype: r, moltype: 'TF',       label: `${r}\nTF` }
				];
		// this was an attempt to rotate the full rank list so that the root node's rank is first, 
		// but it didn't really help and made some cases worse, so I removed it for now
		// if (!rootNode) return full;
		// const rootIdx = full.findIndex(
		// 	(rd) => rd.celltype === rootNode.celltype && rd.moltype === (rootNode.moltype ?? '')
		// );
		// if (rootIdx > 0) {
		// 	return [...full.slice(rootIdx), ...full.slice(0, rootIdx)];
		// }
		return full;
	}

	// defs markers locally (for svg download)
	function defineDefs(svg: d3.Selection<SVGSVGElement, unknown, null, undefined>) {
		const defs = svg.append('defs');

		defs.append('marker')
			.attr('id', 'nbhd-arrow')
			.attr('viewBox', '0 -4 8 8')
			.attr('refX', 8).attr('refY', 0)
			.attr('markerWidth', 6).attr('markerHeight', 6)
			.attr('orient', 'auto')
			.append('path').attr('d', 'M0,-4L8,0L0,4').attr('fill', '#888');

		const blunt = defs.append('marker')
			.attr('id', 'nbhd-blunt')
			.attr('viewBox', '-1 -4 4 8')
			.attr('refX', 2).attr('refY', 0)
			.attr('markerWidth', 6).attr('markerHeight', 6)
			.attr('orient', 'auto');
		blunt.append('line')
			.attr('x1', 0).attr('y1', -4)
			.attr('x2', 0).attr('y2', 4)
			.attr('stroke', '#888').attr('stroke-width', 2);
	}

	function renderTree() {
		if (!$neighborhoodData?.nodes?.length || !$neighborhoodData?.rootId) return;

		if ($neighborhoodData.nodes.length <= 1) {
			d3.select(svgContainer).selectAll('*').remove();
			d3.select(svgContainer)
				.append('text')
				.attr('x', 10).attr('y', 30)
				.attr('fill', '#555').attr('font-size', '12px')
				.text('Searched node not found in current sender-receiver sub-graph.');
			return;
		}

		const W = containerDiv?.clientWidth || 600;
		const H = containerDiv?.clientHeight || 500;
		const PADDING = 24;

		const rootNode = $neighborhoodData.nodes.find((n: any) => n.id === $neighborhoodData.rootId);

		const { nodes: dedupNodes, links: dedupLinks } = groupNodes
			? deduplicateTFs($neighborhoodData.nodes, $neighborhoodData.links)
			: { nodes: $neighborhoodData.nodes, links: $neighborhoodData.links };

		// --- Build rank definitions, filtering to only present combos ---
		const allRankDefs = buildAllRankDefs(rootNode);

		// Find which rankDefs are actually represented in the data
		const presentSet = new Set<number>();
		for (const n of dedupNodes) {
			const ri = allRankDefs.findIndex(
				(rd) => rd.celltype === n.celltype && rd.moltype === (n.moltype ?? '')
			);
			if (ri >= 0) presentSet.add(ri);
		}
		// Preserve order, keep only present ranks
		const rankDefs = allRankDefs.filter((_, i) => presentSet.has(i));
		const numRanks = rankDefs.length || 1;

		// Map node id to rank index in filtered rankDefs
		const rankIndex = new Map<string, number>();
		for (const n of dedupNodes) {
			const ri = rankDefs.findIndex(
				(rd) => rd.celltype === n.celltype && rd.moltype === (n.moltype ?? '')
			);
			rankIndex.set(n.id, ri); // -1 if not found (unclassified)
		}

		// Pixel coordinate along the fixed axis for a given rank index
		const rankToFixed = (ri: number): number => {
			const safeRi = ri < 0 ? (numRanks - 1) / 2 : ri;
			const frac = numRanks === 1 ? 0.5 : safeRi / (numRanks - 1);
			if (isHorizontal) {
				return PADDING + frac * (W - PADDING * 2);
			} else {
				return PADDING + frac * (H - PADDING * 2);
			}
		};

		// --- Apply barycenter sort on a copy of nodes ---
		const nodesCopy = dedupNodes.map((d: any) => ({ ...d }));
		const sorted = barycentreSort(nodesCopy, dedupLinks, rankIndex, numRanks);

		const nodes: any[] = sorted.map((d: any) => {
			const ri = rankIndex.get(d.id) ?? -1;
			const fixed = rankToFixed(ri);
			return isHorizontal ? { ...d, fx: fixed } : { ...d, fy: fixed };
		});

		// Links: shallow copy with raw string ids (d3 will replace source/target objects)
		const links: any[] = dedupLinks.map((l: any) => ({
			...l,
			source: typeof l.source === 'object' ? l.source.id : l.source,
			target: typeof l.target === 'object' ? l.target.id : l.target,
		}));

		d3.select(svgContainer).selectAll('*').remove();
		const svg = d3
			.select(svgContainer)
			.attr('viewBox', `0 0 ${W} ${H}`)
			.style('background', 'transparent')
			.style('cursor', 'grab');
		defineDefs(svg);
		const zoomLayer = svg.append('g').attr('class', 'zoom-layer');
		const zoom = d3
			.zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.1, 20])
			.on('zoom', (event) => zoomLayer.attr('transform', event.transform));
		svg.call(zoom as any);

		// --- Lane background lines + labels ---
		const laneGroup = zoomLayer.append('g').attr('class', 'lanes');
		rankDefs.forEach((rd, ri) => {
			const pos = rankToFixed(ri);
			const labelLines = rd.label.split('\n');

			if (isHorizontal) {
				laneGroup.append('line')
					.attr('x1', pos).attr('y1', 0)
					.attr('x2', pos).attr('y2', H)
					.attr('stroke', '#d8d8d8')
					.attr('stroke-width', 1)
					.attr('stroke-dasharray', '5 4');
				const txt = laneGroup.append('text')
					.attr('text-anchor', 'middle')
					.attr('font-size', '11px')
					.attr('fill', '#000000')
					.attr('font-family', 'sans-serif')
					.attr('pointer-events', 'none');
				labelLines.forEach((line, li) =>
					txt.append('tspan')
						.attr('x', pos)
						.attr('y', H - 4 - (labelLines.length - 1 - li) * 11)
						.text(line)
				);
			} else {
				laneGroup.append('line')
					.attr('x1', 0).attr('y1', pos)
					.attr('x2', W).attr('y2', pos)
					.attr('stroke', '#d8d8d8')
					.attr('stroke-width', 1)
					.attr('stroke-dasharray', '5 4');
				const txt = laneGroup.append('text')
					.attr('text-anchor', 'start')
					.attr('font-size', '11px')
					.attr('fill', '#000000')
					.attr('font-family', 'sans-serif')
					.attr('pointer-events', 'none');
				labelLines.forEach((line, li) =>
					txt.append('tspan')
						.attr('x', 4)
						.attr('y', pos - 2 - (labelLines.length - 1 - li) * 11)
						.text(line)
				);
			}
		});

		const simulation = d3
			.forceSimulation(nodes)
			.force('link', d3.forceLink(links).id((d: any) => d.id).distance(60))
			.force('charge', d3.forceManyBody().strength(-80).distanceMax(120))
			.force('x', isHorizontal ? d3.forceX(W / 2).strength(0) : d3.forceX(W / 2).strength(0.1))
			.force('y', isHorizontal ? d3.forceY(H / 2).strength(0.1) : null as any)
			.force('collide', d3.forceCollide(15))
			.alphaDecay(0.02);

		const linkSel = zoomLayer
			.append('g')
			.attr('class', 'links')
			.selectAll<SVGLineElement, any>('line')
			.data(links)
			.join('line')
			.attr('fill', 'none')
			.call((sel) => aesEdge(sel, 'volcano', 'endShape'));

		const nodeSel = zoomLayer
			.append('g')
			.attr('class', 'nodes')
			.selectAll<SVGGElement, any>('g')
			.data(nodes)
			.join('g')
			.attr('stroke', (d: any) => (d._mergedCount > 1 ? '#000000' : '#fff'))
			.attr('stroke-width', 1)
			.call((sel) => drawNode(sel, $colorScale, true))
			.on('click', (_event: any, d: any) => {
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
			.attr('fill', '#000000')
			.attr('stroke', '#000000')
			.attr('stroke-width', 0.5)
			.attr('pointer-events', 'none')
			.text((d: any) => {
				if (d._mergedCount > 1) return `${d._mergedCount} TFs`;
				return d.name ?? '';
			});

		nodeSel.append('title').text((d: any) => {
			if (d._mergedNames?.length > 1)
				return `Merged TFs (${d._mergedCount}):\n${d._mergedNames.join('\n')}\n(${d.celltype})`;
			return `${d.name}\n(${d.celltype})\n${d.moltype}`;
		});

		// drag only allow movement along the free axis
		nodeSel.call(
			d3.drag<any, any>()
				.on('start', (_e, d) => { if (isHorizontal) d.fy = d.y; else d.fx = d.x; })
				.on('drag',  (e,  d) => { if (isHorizontal) d.fy = e.y; else d.fx = e.x; })
				.on('end',   (_e, d) => { if (isHorizontal) d.fy = null; else d.fx = null; })
		);

		nodeSel
			.on('mouseover', (_e, d: any) => {
				const nbrIds = new Set<string>();
				links.forEach((l: any) => {
					const sid = l.source?.id ?? l.source;
					const tid = l.target?.id ?? l.target;
					if (sid === d.id) nbrIds.add(tid);
					if (tid === d.id) nbrIds.add(sid);
				});
				linkSel.attr('opacity', (l: any) => {
					const sid = l.source?.id ?? l.source;
					const tid = l.target?.id ?? l.target;
					return sid === d.id || tid === d.id ? 1 : 0.06;
				});
				nodeSel.attr('opacity', (n: any) => (n.id === d.id || nbrIds.has(n.id) ? 1 : 0.15));
			})
			.on('mouseout', () => {
				linkSel.attr('opacity', 0.9);
				nodeSel.attr('opacity', 1);
			});

		simulation.on('tick', () => {
			linkSel
				.attr('x1', (d: any) => d.source.x)
				.attr('y1', (d: any) => d.source.y)
				.attr('x2', (d: any) => d.type === 'TFL' ? trimPath(d.source, d.target, 9).x : d.target.x)
				.attr('y2', (d: any) => d.type === 'TFL' ? trimPath(d.source, d.target, 9).y : d.target.y);
			nodeSel.attr('transform', (d: any) => `translate(${d.x ?? 0},${d.y ?? 0})`);
		});

		// Auto-fit after simulation settles
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

	$effect(() => {
		const _data    = $neighborhoodData;
		const _steps   = maxSteps;
		const _group   = groupNodes;
		const _horiz   = isHorizontal;
		renderTree();
	});
</script>

<div class="card border-primary mb-3" style="width: 49%; height: 100%; display: flex; flex-direction: column; min-height: 0;">
	{#if $selectedNodeName}
		<div class="card-header" style="display:flex; align-items:center; gap:8px;">
			<span> {$selectedNodeName} Neighborhood </span>
			<div style="margin-left: auto; display: flex; align-items: center; gap: 8px;">
				<label for="input-maxSteps" style="font-size: 11px; margin: 0; white-space: nowrap;">max steps:</label>
				<input
					id="input-maxSteps"
					type="number"
					bind:value={maxSteps}
					min="1"
					max="5"
					style="width: 52px; padding: 2px 6px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px;"
				/>
				<button
					onclick={() => { isHorizontal = !isHorizontal; }}
					style="padding: 2px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; display: flex; align-items: center; gap: 4px;"
					title="Toggle layout orientation"
				>
					{#if isHorizontal}
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
							<line x1="7" y1="1" x2="7" y2="13" />
							<line x1="3" y1="4" x2="7" y2="1" /><line x1="11" y1="4" x2="7" y2="1" />
						</svg>
						Vertical
					{:else}
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
							<line x1="1" y1="7" x2="13" y2="7" />
							<line x1="10" y1="3" x2="13" y2="7" /><line x1="10" y1="11" x2="13" y2="7" />
						</svg>
						Horizontal
					{/if}
				</button>
				<GroupToggle bind:checked={groupNodes} label="Group TFs" />
				<button
					onclick={handleDownloadSVG}
					style="font-size:11px; padding:2px 9px; background:transparent; color:#444; border-radius:4px; border:1px solid #bbb; cursor:pointer; display:flex; gap:4px; margin-right:6px;"
				>Download SVG</button>
			</div>
		</div>
		<div bind:this={containerDiv} class="card-body" style="flex: 1; min-height: 0; padding: 0.5rem;">
			<svg bind:this={svgContainer} style="width: 100%; height: 100%; display: block;"></svg>
		</div>
	{:else}
		<div class="card-header" style="display:flex; align-items:center; gap:8px;">
			<span>Neighborhood View</span>
		</div>
		<div class="card-body">
			<p style="font-size: 12px; color: #000000;">Select a node in the full network to view its neighborhood.</p>
		</div>
	{/if}	
</div>