<script lang="ts">
	import * as d3 from 'd3';
	import {
		sender,
		receiver,
		colorScale,
		reverseSig,
		selectedNode,
		selectedNodeName
	} from '$lib/stores';
	import { aesEdge, drawNode, defineMarkers, drawLegend, trimPath } from './utils';

	export let neighborhoodData: {
		nodes: any[];
		links: any[];
		rootId: number;
	};

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

	// TF nodes are merged if identical sets of:
	//   - outgoing links (same target id + weight)
	//   - incoming links (same source id + weight)
	function deduplicateTFs(rawNodes: any[], rawLinks: any[]): { nodes: any[]; links: any[] } {
		const tfNodes = rawNodes.filter((n) => n.moltype === 'TF');
		const nonTFNodes = rawNodes.filter((n) => n.moltype !== 'TF');

		// signature for each TF node
		const sig = (n: any): string => {
			const out = rawLinks
				.filter((l) => l.source === n.id)
				.map((l) => `o:${l.target}:${l.weight}`)
				.sort()
				.join('|');
			const inc = rawLinks
				.filter((l) => l.target === n.id)
				.map((l) => `i:${l.source}:${l.weight}`)
				.sort()
				.join('|');
			return `${out}__${inc}`;
		};
		// Group TFs by signature
		const groups = new Map<string, any[]>();
		for (const n of tfNodes) {
			const s = sig(n);
			if (!groups.has(s)) groups.set(s, []);
			groups.get(s)!.push(n);
		}
		// For each group, keep one representative node; record all names
		const mergedTFs: any[] = [];
		// Map from old id to representative id
		const idMap = new Map<number, number>();

		for (const [, members] of groups) {
			const rep = { ...members[0] }; // representative node
			rep._mergedNames = members.map((m) => m.name);
			rep._mergedCount = members.length;
			rep._mergedIds = members.map((m) => m.id);
			mergedTFs.push(rep);
			for (const m of members) idMap.set(m.id, rep.id);
		}

		// Remap links, then deduplicate identical remapped links
		const remappedLinks = rawLinks.map((l) => ({
			...l,
			source: idMap.get(l.source) ?? l.source,
			target: idMap.get(l.target) ?? l.target
		}));

		const seenLinks = new Set<string>();
		const dedupedLinks = remappedLinks.filter((l) => {
			const k = `${l.source}-${l.target}-${l.type}-${l.weight}`;
			if (seenLinks.has(k)) return false;
			seenLinks.add(k);
			return true;
		});

		return {
			nodes: [...nonTFNodes, ...mergedTFs],
			links: dedupedLinks
		};
	}

	function renderTree() {
		if (!neighborhoodData?.nodes?.length || !neighborhoodData?.rootId) return;

		const W = containerDiv?.clientWidth || 600;
		const H = containerDiv?.clientHeight || 500;

		const PADDING = 100;
		const numRanks = $reverseSig ? 4 : 6;
		const yForRank = (rank: number) => PADDING + (rank / (numRanks - 1)) * (H - PADDING * 3); // + d3.randomUniform(-4, 4)();

		// Deduplicate TFs
		const { nodes: dedupNodes, links: dedupLinks } = deduplicateTFs(
			neighborhoodData.nodes,
			neighborhoodData.links
		);

		// Attach fy
		const nodes = dedupNodes.map((d) => ({
			...d,
			fy: yForRank(getYRank(d))
		}));
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
			.force(
				'link',
				d3.forceLink(simLinks).id((d: any) => d.id)
				// .distance(80)
			)
			.force('charge', d3.forceManyBody().strength(-80).distanceMax(50))
			.force('x', d3.forceX(W / 2).strength(0.1))
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
			.attr('text-anchor', 'middle')
			.attr('dy', '2em') // below the node shape
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
					if (!e.active) simulation.alphaTarget(0.3).restart();
					d.fx = d.x;
				})
				.on('drag', (e, d) => {
					d.fx = e.x;
				})
				.on('end', (e, d) => {
					if (!e.active) simulation.alphaTarget(0);
					d.fx = null;
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
						end = trimPath(d.source, d.target, 10);
					}
					const dx = d.target.x - d.source.x;
					const dy = d.target.y - d.source.y;
					const dr = Math.sqrt(dx * dx + dy * dy); // radius for arc
					// const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // increase curvature by multiplying
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
		// drawLegend(svgContainer, $colorScale, 'volcano', 'endShape', $sender, $receiver, true);
	}

	$: if (neighborhoodData) renderTree();
</script>

<div bind:this={containerDiv} style="width: 100%; height: 100%;">
	<svg bind:this={svgContainer} style="width: 100%; height: 100%;"></svg>
</div>
