<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import {
		selectedNode,
		sender,
		receiver,
		colorScale,
		colorCT
	} from '$lib/stores';

	interface NeighborNode {
		id: string;
		name: string;
		celltype: string;
		moltype: string;
		distance: number;
		[key: string]: any;
	}
	interface NeighborLink {
		source: string;
		target: string;
		type: 'LR' | 'TFL' | 'RTF';
		weight?: number;
		[key: string]: any;
	}
	interface NeighborhoodData {
		nodes: NeighborNode[];
		links: NeighborLink[];
		rootId: string;
	}

	export let comparison: string = '';
	export let apiBase: string = '';

	let svgEl: SVGSVGElement;
	let data: NeighborhoodData | null = null;
	let loading = false;
	let error = '';

	const W = 680;
	const ROW_H = 72;       // px per lane
	const NODE_R = 18;
	const LABEL_H = 12;     // font-size for name label
	const SUBLABEL_H = 10;  // font-size for moltype/celltype

	// Lane order: mirrors the circular view ring order
	const LANE_ORDER: Array<{ moltype: string; celltype: 'sender' | 'receiver' }> = [
		{ moltype: 'TF',       celltype: 'sender'   },
		{ moltype: 'ligand',   celltype: 'sender'   },
		{ moltype: 'receptor', celltype: 'receiver' },
		{ moltype: 'TF',       celltype: 'receiver' },
	];

	function laneKey(moltype: string, celltype: string): string {
		const role = celltype === $sender ? 'sender' : celltype === $receiver ? 'receiver' : celltype;
		return `${moltype}|${role}`;
	}
	function laneIndex(node: NeighborNode): number {
		const role = node.celltype === $sender ? 'sender' : node.celltype === $receiver ? 'receiver' : null;
		if (!role) return LANE_ORDER.length; // extra lane for unexpected types
		return LANE_ORDER.findIndex(l => l.moltype === node.moltype && l.celltype === role);
	}

	function laneLabel(i: number): string {
		if (i >= LANE_ORDER.length) return 'other';
		const l = LANE_ORDER[i];
		const ct = l.celltype === 'sender' ? $sender : $receiver;
		return `${ct} · ${l.moltype}`;
	}

	async function fetchNeighborhood(nodeId: string) {
		if (!nodeId || !comparison) return;
		loading = true;
		error = '';
		data = null;
		try {
			const url = `${apiBase}/api/node_neighborhood?node_id=${encodeURIComponent(nodeId)}&comparison=${encodeURIComponent(comparison)}&max_steps=4`;
			const res = await fetch(url);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			data = await res.json();
			renderTree();
		} catch (e: any) {
			error = e.message ?? 'Failed to fetch neighborhood';
		} finally {
			loading = false;
		}
	}

	function renderTree() {
		if (!svgEl || !data) return;

		const { nodes, links, rootId } = data;
		if (!nodes.length) return;

		const laneSet = new Set<number>();
		nodes.forEach(n => laneSet.add(laneIndex(n)));
		const laneCount = Math.max(...laneSet) + 1;

		const H = (laneCount + 1) * ROW_H;
		const svg = d3.select(svgEl)
			.attr('viewBox', `0 0 ${W} ${H}`)
			.attr('width', '100%')
			.attr('height', H);
		svg.selectAll('*').remove();

		const defs = svg.append('defs');

		defs.append('pattern')
			.attr('id', 'nt-grid')
			.attr('width', 20).attr('height', 20)
			.attr('patternUnits', 'userSpaceOnUse')
			.append('path')
			.attr('d', 'M 20 0 L 0 0 0 20')
			.attr('fill', 'none').attr('stroke', '#2a2a3a').attr('stroke-width', 0.5);

		const markerDefs = [
			{ id: 'arrow-LR',  color: '#60a5fa' },
			{ id: 'arrow-TFL', color: '#a78bfa' },
			{ id: 'arrow-RTF', color: '#34d399' },
		];
		markerDefs.forEach(({ id, color }) => {
			defs.append('marker')
				.attr('id', id)
				.attr('markerWidth', 7).attr('markerHeight', 7)
				.attr('refX', 6).attr('refY', 3)
				.attr('orient', 'auto')
				.append('path')
				.attr('d', 'M 0 0 L 7 3 L 0 6 Z')
				.attr('fill', color);
		});

		// Glow filter for root node
		const glow = defs.append('filter').attr('id', 'nt-glow');
		glow.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'coloredBlur');
		const feMerge = glow.append('feMerge');
		feMerge.append('feMergeNode').attr('in', 'coloredBlur');
		feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

		svg.append('rect')
			.attr('width', W).attr('height', H)
			.attr('fill', '#0f0f1a');

		svg.append('rect')
			.attr('width', W).attr('height', H)
			.attr('fill', 'url(#nt-grid)');

		// lanes
		const laneGroup = svg.append('g').attr('class', 'lanes');

		d3.range(laneCount).forEach(i => {
			const y = ROW_H / 2 + i * ROW_H;
			const isEven = i % 2 === 0;
			laneGroup.append('rect')
				.attr('x', 0).attr('y', i * ROW_H)
				.attr('width', W).attr('height', ROW_H)
				.attr('fill', isEven ? 'rgba(255,255,255,0.018)' : 'transparent');
			// Lane separator line
			laneGroup.append('line')
				.attr('x1', 0).attr('y1', i * ROW_H)
				.attr('x2', W).attr('y2', i * ROW_H)
				.attr('stroke', '#1e1e30').attr('stroke-width', 1);
			// Lane label 
			laneGroup.append('text')
				.attr('x', 8).attr('y', y)
				.attr('dominant-baseline', 'central')
				.attr('font-size', '9px')
				.attr('font-family', 'monospace')
				.attr('letter-spacing', '0.08em')
				.attr('fill', '#3d3d5c')
				.attr('text-transform', 'uppercase')
				.text(laneLabel(i).toUpperCase());
			// Lane separator on right side too for balance
			laneGroup.append('line')
				.attr('x1', 0).attr('y1', (i + 1) * ROW_H)
				.attr('x2', W).attr('y2', (i + 1) * ROW_H)
				.attr('stroke', '#1e1e30').attr('stroke-width', 1);
		});

		// ── compute x positions within each lane ─────────────────────────
		// Group nodes by lane, sort within lane by distance then name
		const byLane = new Map<number, NeighborNode[]>();
		nodes.forEach(n => {
			const li = laneIndex(n);
			if (!byLane.has(li)) byLane.set(li, []);
			byLane.get(li)!.push(n);
		});

		// Label column width on left 
		const LABEL_COL = 110;
		const nodePos = new Map<string, { x: number; y: number }>();
		byLane.forEach((laneNodes, li) => {
			laneNodes.sort((a, b) => a.distance - b.distance || a.name.localeCompare(b.name));
			const count = laneNodes.length;
			const usable = W - LABEL_COL - 20;
			laneNodes.forEach((n, i) => {
				const x = LABEL_COL + (i + 0.5) * (usable / count);
				const y = ROW_H / 2 + li * ROW_H;
				nodePos.set(n.id, { x, y });
			});
		});

		// Links: build a node map for quick lookup
		const nodeById = new Map<string, NeighborNode>(nodes.map(n => [n.id, n]));

		const linkColor: Record<string, string> = {
			LR:  '#60a5fa',
			TFL: '#a78bfa',
			RTF: '#34d399',
		};

		const linkGroup = svg.append('g').attr('class', 'links');

		links.forEach(l => {
			const sp = nodePos.get(l.source);
			const tp = nodePos.get(l.target);
			if (!sp || !tp) return;

			const color = linkColor[l.type] ?? '#888';
			const isLR = l.type === 'LR';

			// Curved path (quadratic bezier with midpoint offset)
			const mx = (sp.x + tp.x) / 2;
			const my = (sp.y + tp.y) / 2 - (isLR ? 0 : 18);

			const markerId = `arrow-${l.type}`;

			// For LR (undirected) draw a simple arc; for others draw directed
			if (isLR) {
				// Bidirectional: draw as a thicker undirected arc
				linkGroup.append('path')
					.attr('d', `M ${sp.x},${sp.y} Q ${mx},${my} ${tp.x},${tp.y}`)
					.attr('fill', 'none')
					.attr('stroke', color)
					.attr('stroke-width', 1.5)
					.attr('stroke-opacity', 0.55)
					.attr('stroke-dasharray', '5 3');
			} else {
				// Directed arrow
				const dx = tp.x - sp.x;
				const dy = tp.y - sp.y;
				const len = Math.sqrt(dx * dx + dy * dy) || 1;
				// Shorten target end to not overlap node circle
				const ex = tp.x - (dx / len) * (NODE_R + 6);
				const ey = tp.y - (dy / len) * (NODE_R + 6);

				linkGroup.append('path')
					.attr('d', `M ${sp.x},${sp.y} Q ${mx},${my} ${ex},${ey}`)
					.attr('fill', 'none')
					.attr('stroke', color)
					.attr('stroke-width', 1.5)
					.attr('stroke-opacity', 0.7)
					.attr('marker-end', `url(#${markerId})`);
			}
		});

		function nodeColor(n: NeighborNode): string {
			try {
				return ($colorScale as any)(n.name) ?? '#888';
			} catch {
				return '#888';
			}
		}
		function ctColor(n: NeighborNode): string {
			try {
				return ($colorCT as any)(n.celltype) ?? '#555';
			} catch {
				return '#555';
			}
		}

		const nodeGroup = svg.append('g').attr('class', 'nodes');

		nodes.forEach(n => {
			const pos = nodePos.get(n.id);
			if (!pos) return;
			const isRoot = n.id === rootId;
			const g = nodeGroup.append('g')
				.attr('transform', `translate(${pos.x},${pos.y})`)
				.attr('cursor', 'pointer');

			// Outer ring for celltype color
			g.append('circle')
				.attr('r', NODE_R + 3)
				.attr('fill', ctColor(n))
				.attr('fill-opacity', 0.25)
				.attr('stroke', ctColor(n))
				.attr('stroke-width', isRoot ? 2.5 : 1.5)
				.attr('stroke-opacity', isRoot ? 1 : 0.5)
				.attr('filter', isRoot ? 'url(#nt-glow)' : null);

			// Main node circle
			g.append('circle')
				.attr('r', NODE_R)
				.attr('fill', nodeColor(n))
				.attr('fill-opacity', isRoot ? 1 : 0.82)
				.attr('stroke', isRoot ? '#fff' : 'rgba(255,255,255,0.25)')
				.attr('stroke-width', isRoot ? 2 : 1);

			// Distance badge (skip for root)
			if (!isRoot) {
				g.append('circle')
					.attr('cx', NODE_R - 2).attr('cy', -(NODE_R - 2))
					.attr('r', 7)
					.attr('fill', '#1a1a2e')
					.attr('stroke', '#3d3d70')
					.attr('stroke-width', 1);
				g.append('text')
					.attr('x', NODE_R - 2).attr('y', -(NODE_R - 2))
					.attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
					.attr('font-size', '8px').attr('font-family', 'monospace')
					.attr('fill', '#a0a0cc')
					.text(n.distance);
			}

			// Moltype glyph inside node
			const glyphs: Record<string, string> = { ligand: 'L', receptor: 'R', TF: 'T' };
			g.append('text')
				.attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
				.attr('font-size', '10px').attr('font-family', 'monospace')
				.attr('font-weight', 'bold')
				.attr('fill', 'rgba(0,0,0,0.65)')
				.text(glyphs[n.moltype] ?? '?');

			// Name label below node
			g.append('text')
				.attr('y', NODE_R + LABEL_H + 2)
				.attr('text-anchor', 'middle')
				.attr('font-size', `${LABEL_H}px`)
				.attr('font-family', '"IBM Plex Mono", monospace')
				.attr('fill', isRoot ? '#ffffff' : '#c0c0d8')
				.attr('font-weight', isRoot ? '600' : '400')
				.text(n.name);

			// Tooltip
			g.append('title').text(`${n.name}\nCelltype: ${n.celltype}\nMoltype: ${n.moltype}\nDistance: ${n.distance}`);
		});

		// ── legend ──────────────────────────────────────────────────────
		const legY = H - 18;
		const legData = [
			{ label: 'LR (undirected)', color: '#60a5fa', dash: '5 3' },
			{ label: 'TFL',             color: '#a78bfa', dash: null  },
			{ label: 'RTF',             color: '#34d399', dash: null  },
		];
		const legG = svg.append('g').attr('transform', `translate(${LABEL_COL},${legY})`);
		legData.forEach(({ label, color, dash }, i) => {
			const lx = i * 155;
			legG.append('line')
				.attr('x1', lx).attr('y1', 0).attr('x2', lx + 24).attr('y2', 0)
				.attr('stroke', color).attr('stroke-width', 2)
				.attr('stroke-dasharray', dash ?? null);
			if (!dash) {
				legG.append('polygon')
					.attr('points', `${lx + 22},0 ${lx + 16},-3 ${lx + 16},3`)
					.attr('fill', color);
			}
			legG.append('text')
				.attr('x', lx + 28).attr('y', 1)
				.attr('dominant-baseline', 'central')
				.attr('font-size', '9px').attr('font-family', 'monospace')
				.attr('fill', '#7070a0')
				.text(label);
		});
	}

	let prevNodeId = '';
	$: if ($selectedNode && $selectedNode !== prevNodeId) {
		prevNodeId = $selectedNode;
		fetchNeighborhood($selectedNode);
	}

	onMount(() => {
		if ($selectedNode) fetchNeighborhood($selectedNode);
	});

	onDestroy(() => {});
</script>

<div class="neighborhood-tree">
	<div class="nt-header">
		<span class="nt-title">Neighborhood</span>
		{#if $selectedNode}
			<span class="nt-subtitle">↳ <em>{$selectedNode}</em> · up to 4 steps</span>
		{/if}
	</div>

	{#if !$selectedNode}
		<div class="nt-empty">
			<span>Select a node in the network to explore its neighborhood</span>
		</div>
	{:else if loading}
		<div class="nt-loading">
			<div class="nt-spinner" />
			<span>Fetching neighbors…</span>
		</div>
	{:else if error}
		<div class="nt-error">{error}</div>
	{:else if data && !data.nodes.length}
		<div class="nt-empty"><span>No neighbors found.</span></div>
	{:else}
		<svg bind:this={svgEl}></svg>
	{/if}
</div>

<style>
	.neighborhood-tree {
		background: #0f0f1a;
		border: 1px solid #1e1e38;
		border-radius: 6px;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		font-family: 'IBM Plex Mono', monospace;
	}

	.nt-header {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 10px 14px 8px;
		border-bottom: 1px solid #1e1e38;
		background: rgba(255, 255, 255, 0.02);
	}

	.nt-title {
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #8080b0;
	}

	.nt-subtitle {
		font-size: 11px;
		color: #5050a0;
	}

	.nt-subtitle em {
		color: #a0a0d0;
		font-style: normal;
	}

	.nt-empty,
	.nt-loading,
	.nt-error {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		padding: 40px 20px;
		font-size: 12px;
		color: #4040668;
	}

	.nt-empty span { color: #3d3d66; }
	.nt-error     { color: #f87171; }

	.nt-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid #2a2a4a;
		border-top-color: #6060b0;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	svg {
		display: block;
		width: 100%;
	}
</style>
