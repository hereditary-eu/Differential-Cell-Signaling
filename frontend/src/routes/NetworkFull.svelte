<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { NetworkLens } from './NetworkLens';
	import { downloadSVG } from './downloadSVG';
	import { selectedComparison } from '$lib/stores';
	export let fullNet: { nodes: any[]; links: any[]; stats?: any };

	let svgEl: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let labelSimulation: d3.Simulation<any, undefined>;
	let metric: 'betweenness' | 'pagerank' = 'pagerank';
	let resizeObserver: ResizeObserver;
	let lensEnabled = false;

	let svgW = 900;
	let svgH = 380;
	const LEGEND_COL_W = 130; //pixels width for legend

	// One lens instance for the lifetime of this component
	const lens = new NetworkLens({ radius: 80, zoom: 3.5, metric });

	function buildSizeScale(nodes: any[], key: 'betweenness' | 'pagerank') {
		const extent = d3.extent(nodes, (d) => d[key]) as [number, number];
		return d3.scaleSqrt().domain(extent).range([2, 13]).clamp(true);
	}

	function isOutlier(d: any, key: 'betweenness' | 'pagerank') {
		return key === 'betweenness' ? d.is_outlier_b : d.is_outlier_p;
	}

	function getThreshold(key: 'betweenness' | 'pagerank') {
		if (!fullNet?.stats) return undefined;
		return key === 'betweenness'
			? fullNet.stats.b_outlierThreshold
			: fullNet.stats.p_outlierThreshold;
	}
	function getTopMols(key: 'betweenness' | 'pagerank') {
		if (!fullNet?.stats) return undefined;
		return key === 'betweenness' ? fullNet.stats.b_topMols : fullNet.stats.p_topMols;
	}
	function drawLegendAndViolin(
		svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
		sizeScale: d3.ScalePower<number, number>,
		threshold: number,
		topMols: string[],
		W: number,
		H: number
	) {
		const colW = Math.max(80, Math.min(LEGEND_COL_W, W * 0.16));
		const cx = colW * 0.55;
		const halfW = colW * 0.3;
		const g = svg.append('g').attr('transform', `translate(14, 0)`);
		const fontSize = Math.max(10, Math.min(14, H * 0.036));
		// outlier legend dot
		const dotY = fontSize + 12;
		g.append('circle').attr('cx', 5).attr('cy', dotY).attr('r', 4).attr('fill', '#e03333');
		g.append('text')
			.attr('x', 13)
			.attr('y', dotY)
			.attr('dominant-baseline', 'middle')
			.attr('font-size', `${Math.max(9, fontSize - 2)}px`)
			.attr('fill', '#555')
			.text(threshold != null ? `Outlier (> ${threshold.toFixed(4)})` : 'outlier');

		// size legend
		const sLegendY = dotY + 20;
		const domain = sizeScale.domain();
		const mid = (domain[0] + domain[1]) / 2;
		const spacing = (colW - 10) / 2;
		[domain[0], mid, domain[1]].forEach((v, i) => {
			const r = sizeScale(v);
			const x = i * spacing + 5;
			g.append('circle')
				.attr('cx', x)
				.attr('cy', sLegendY + 10 - r)
				.attr('r', r)
				.attr('fill', '#888')
				.attr('fill-opacity', 0.6);
			g.append('text')
				.attr('x', x)
				.attr('y', sLegendY + 22)
				.attr('text-anchor', 'middle')
				.attr('font-size', `${Math.max(9, fontSize - 2)}px`)
				.attr('fill', '#777')
				.text(['Low', 'Mid', 'High'][i]);
		});

		// Violin + jitter
		const values = fullNet.nodes
			.map((d) => ({ v: d[metric] as number, outlier: isOutlier(d, metric) }))
			.filter((d) => d.v != null);

		const VPAD_TOP = sLegendY + 34; // y-pixel where violin top starts (below legend)
		const VPAD_BOT = 6; // bottom margin inside the SVG
		const violinH = Math.min(
			180,
			H - VPAD_TOP - VPAD_BOT - (topMols ? topMols.length * 18 + 22 : 0)
		);

		const yScale = d3
			.scaleLinear()
			.domain(d3.extent(values, (d) => d.v) as [number, number])
			.range([VPAD_TOP + violinH, VPAD_TOP])
			.nice();

		const bandwidth = (yScale.domain()[1] - yScale.domain()[0]) * 0.08;
		const ticks = yScale.ticks(40);
		function kde(v: number) {
			return (
				d3.mean(
					values,
					(d) =>
						Math.exp(-0.5 * ((v - d.v) / bandwidth) ** 2) / (bandwidth * Math.sqrt(2 * Math.PI))
				) ?? 0
			);
		}
		const density = ticks.map((t) => ({ t, d: kde(t) }));
		const maxD = d3.max(density, (d) => d.d) ?? 1;
		const xViol = d3.scaleLinear().domain([0, maxD]).range([0, halfW]);

		// violin body
		const area = d3
			.area<{ t: number; d: number }>()
			.y((d) => yScale(d.t))
			.x0((d) => cx - xViol(d.d))
			.x1((d) => cx + xViol(d.d))
			.curve(d3.curveCatmullRom);

		g.append('path')
			.datum(density)
			.attr('d', area)
			.attr('fill', '#ddd')
			.attr('stroke', '#aaa')
			.attr('stroke-width', 0.8);

		// IQR box
		const sorted = values.map((d) => d.v).sort(d3.ascending);
		const q1 = d3.quantile(sorted, 0.25)!;
		const q3 = d3.quantile(sorted, 0.75)!;
		const med = d3.quantile(sorted, 0.5)!;
		g.append('rect')
			.attr('x', cx - halfW * 0.35)
			.attr('y', yScale(q3))
			.attr('width', halfW * 0.7)
			.attr('height', yScale(q1) - yScale(q3))
			.attr('fill', '#fff')
			.attr('stroke', '#555')
			.attr('stroke-width', 0.8);
		g.append('line')
			.attr('x1', cx - halfW * 0.35)
			.attr('x2', cx + halfW * 0.35)
			.attr('y1', yScale(med))
			.attr('y2', yScale(med))
			.attr('stroke', '#222')
			.attr('stroke-width', 1.5);

		// threshold line
		if (threshold != null) {
			g.append('line')
				.attr('x1', cx - halfW)
				.attr('x2', cx + halfW)
				.attr('y1', yScale(threshold))
				.attr('y2', yScale(threshold))
				.attr('stroke', '#e03333')
				.attr('stroke-width', 1)
				.attr('stroke-dasharray', '3,2');
		}

		// jitter
		const rng = d3.randomLcg(42); // seeded so dots don't jump on re-render
		const jitter = d3.randomNormal.source(rng)(0, halfW * 0.22);
		values.forEach((d) => {
			g.append('circle')
				.attr('cx', cx + jitter())
				.attr('cy', yScale(d.v))
				.attr('r', 1.8)
				.attr('fill', d.outlier ? '#e03333' : '#333')
				.attr('fill-opacity', d.outlier ? 0.9 : 0.25);
		});

		// y-axis (right side of violin)
		const axis = d3.axisRight(yScale).ticks(4).tickFormat(d3.format('.2~e'));
		g.append('g')
			.attr('transform', `translate(${cx + halfW}, 0)`)
			.call(axis)
			.call((ax) => {
				ax.selectAll('text')
					.attr('font-size', `${Math.max(9, fontSize - 2)}px`)
					.attr('fill', '#888');
				ax.selectAll('line,path').attr('stroke', '#ccc');
			});
		if (topMols?.length) {
			const listY = VPAD_TOP + violinH + 20;
			const rowH = Math.max(14, Math.min(18, H * 0.04));
			g.append('text')
				.attr('x', 0)
				.attr('y', listY)
				.attr('font-size', `${Math.max(9, fontSize - 2)}px`)
				.attr('fill', '#555')
				.text('Top 5:');

			topMols.forEach((mol, i) => {
				g.append('text')
					.attr('x', 0)
					.attr('y', listY + 14 + i * rowH)
					.attr('font-size', `${Math.max(9, fontSize - 2)}px`)
					.attr('fill', '#444')
					.text(`${i + 1}. ${mol}`);
			});
		}
	}
	function render() {
		if (!fullNet?.nodes?.length) return;
		simulation?.stop();

		const W = svgW;
		const H = svgH;
		const netW = W;

		const nodes = fullNet.nodes.map((d) => ({ ...d }));
		const links = fullNet.links.map((d) => ({ ...d }));
		const sizeScale = buildSizeScale(nodes, metric);
		const threshold = getThreshold(metric);
		const topMols = getTopMols(metric);

		const outlierNodes = nodes.filter((d) => isOutlier(d, metric));
		const metricExtent = d3.extent(outlierNodes, (d) => d[metric]) as [number, number];
		const opacityScale = d3.scaleLinear().domain(metricExtent).range([0.5, 1.0]).clamp(true);
		const labelFontScale = d3.scaleLinear().domain(metricExtent).range([3, 10]).clamp(true);

		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();
		svg.attr('viewBox', [0, 0, W, H]).style('background', 'transparent').style('cursor', 'grab');

		const zoomLayer = svg.append('g');
		const zoom = d3
			.zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.15, 6])
			.on('zoom', (e) => {
				zoomLayer.attr('transform', e.transform);
				lens.setZoomTransform(e.transform);
			});
		svg.call(zoom as any);

		const link = zoomLayer
			.append('g')
			.attr('stroke', '#bbb')
			.attr('stroke-opacity', 0.5)
			.attr('stroke-width', 0.6)
			.selectAll('line')
			.data(links)
			.join('line');

		const node = zoomLayer
			.append('g')
			.selectAll('circle')
			.data(nodes)
			.join('circle')
			.attr('r', (d) => sizeScale(d[metric] ?? 0))
			.attr('fill', (d) => (isOutlier(d, metric) ? '#e03333' : '#888'))
			.attr('fill-opacity', (d) => (isOutlier(d, metric) ? 0.9 : 0.55))
			.attr('stroke', (d) => (isOutlier(d, metric) ? '#a00' : '#555'))
			.attr('stroke-width', (d) => (isOutlier(d, metric) ? 1.2 : 0.4));

		node
			.append('title')
			.text(
				(d: any) =>
					`${d.name} (${d.celltype})\nbetweenness: ${d.betweenness?.toFixed(4) ?? 'n/a'}\npagerank: ${d.pagerank?.toFixed(4) ?? 'n/a'}`
			);
		const labelLayer = zoomLayer.append('g').attr('class', 'label-layer');
		const labelData = outlierNodes.map((d) => ({
			nodeRef: d,
			lx: d.x ?? 0,
			ly: d.y ?? 0
		}));
		const labels = labelLayer
			.selectAll('text.outlier-label')
			.data(labelData)
			.join('text')
			.attr('class', 'outlier-label')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'middle')
			.attr('pointer-events', 'none')
			.attr('fill', '#780000')
			.attr('font-weight', '600')
			.attr('font-family', 'sans-serif')
			.attr('font-size', (d) => `${labelFontScale(d.nodeRef[metric])}px`)
			.attr('fill-opacity', (d) => opacityScale(d.nodeRef[metric]))
			.text((d) => d.nodeRef.name);

		// LENS
		lens.metric = metric;
		lens.setSvgSize(W, H);
		lens.setData(nodes, links);
		lens.setSizeScale(sizeScale);
		lens.setEnabled(lensEnabled);
		lens.mount(svg, svgEl); // rebuilds DOM + attaches mouse events

		simulation = d3
			.forceSimulation(nodes)
			.alphaDecay(0.04)
			.velocityDecay(0.4)
			.force(
				'link',
				d3
					.forceLink(links)
					.id((d: any) => d.id)
					.distance(12)
					.strength(0.3)
			)
			.force('charge', d3.forceManyBody().strength(-25).distanceMax(140))
			.force('center', d3.forceCenter(netW / 2, H / 2))
			.force(
				'collide',
				d3.forceCollide((d: any) => sizeScale(d[metric] ?? 0) + 1)
			);
		labelSimulation = d3
			.forceSimulation(labelData as any)
			.alphaDecay(0.02)
			.velocityDecay(0.3)
			.force('anchor', () => {
				for (const d of labelData as any[]) {
					const nx = d.nodeRef.x ?? 0;
					const ny = d.nodeRef.y ?? 0;
					const dx = nx - d.x;
					const dy = ny - d.y;
					const dist = Math.sqrt(dx * dx + dy * dy);
					const maxDist = 15;
					const strength = Math.min(1, dist / maxDist) * 0.08;
					d.vx += dx * strength;
					d.vy += dy * strength;
					// d.vy -= 0.4; // to prefer labels not on top of node
				}
			});

		simulation.on('tick', () => {
			link
				.attr('x1', (d: any) => d.source.x)
				.attr('y1', (d: any) => d.source.y)
				.attr('x2', (d: any) => d.target.x)
				.attr('y2', (d: any) => d.target.y);
			node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
			labelSimulation.alpha(Math.max(labelSimulation.alpha(), simulation.alpha() * 0.6));
			lens.refreshIfActive(sizeScale);
		});
		labelSimulation.on('tick', () => {
			labels.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y);
		});
		node.call(
			d3.drag<any, any>().on('drag', (e, d) => {
				d.fx = e.x;
				d.fy = e.y;
			})
		);
		drawLegendAndViolin(svg, sizeScale, threshold, topMols, W, H);
	}

	function switchMetric(m: 'betweenness' | 'pagerank') {
		metric = m;
		render();
	}
	function toggleLens() {
		lensEnabled = !lensEnabled;
		lens.setEnabled(lensEnabled);
		lensEnabled = lensEnabled;
	}
	function handleDownloadSVG() {
		downloadSVG(svgEl, `${$selectedComparison}_fullNetVis_${metric}.svg`);
	}
	$: if (fullNet?.nodes?.length) render();
	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				if (width > 0 && height > 0) {
					svgW = width;
					svgH = height;
					lens.setSvgSize(width, height);
					render();
				}
			}
		});
		resizeObserver.observe(svgEl);
		render();
	});
	onDestroy(() => {
		simulation?.stop();
		resizeObserver?.disconnect();
		lens.destroy();
	});
</script>

<div
	style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; margin-left: 4px; margin-top: 3px; "
>
	<span style="font-size: 12px; color: #666; margin-left: 4px;">Metric:</span>
	<button
		style="font-size: 12px; padding: 2px 10px; border-radius: 4px; border: 1px solid #bbb;
			background: {metric === 'pagerank' ? '#e03333' : 'transparent'};
			color: {metric === 'pagerank' ? '#fff' : 'inherit'}; cursor: pointer;"
		onclick={() => switchMetric('pagerank')}
	>
		PageRank
	</button>
	<button
		style="font-size: 12px; padding: 2px 10px; border-radius: 4px; border: 1px solid #bbb;
			background: {metric === 'betweenness' ? '#e03333' : 'transparent'};
			color: {metric === 'betweenness' ? '#fff' : 'inherit'}; cursor: pointer;"
		onclick={() => switchMetric('betweenness')}
	>
		Betweenness
	</button>

	<span style="margin-left:auto; margin-right:6px;">
		<button
			onclick={toggleLens}
			style="font-size:12px; padding:2px 9px; border-radius:4px; border:1px solid #bbb;
				background:{lensEnabled ? '#000000' : 'transparent'};
				color:{lensEnabled ? '#fff' : '#444'}; cursor:pointer;
				display:flex; gap:4px;"
		>
			<!-- magnifier icon -->
			<svg
				width="13"
				height="13"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2.2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<circle cx="11" cy="11" r="8" />
				<line x1="21" y1="21" x2="16.65" y2="16.65" />
				<line x1="11" y1="8" x2="11" y2="14" />
				<line x1="8" y1="11" x2="14" y2="11" />
			</svg>
			Lens
		</button>
	</span>
	<button
		onclick={handleDownloadSVG}
		style="font-size:12px; padding:2px 9px; 
				background:'transparent'; color:'#444';
				border-radius:4px; border:1px solid #bbb;
				cursor:pointer;
				display:flex; gap:4px; margin-right:6px; ">Download SVG</button
	>
</div>

<svg bind:this={svgEl} style="width:100%; height:100%;"></svg>
