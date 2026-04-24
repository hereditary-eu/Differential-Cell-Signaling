<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';

	export let fullNet: { nodes: any[]; links: any[]; stats?: any };

	let svgEl: SVGSVGElement;
	let simulation: d3.Simulation<any, undefined>;
	let metric: 'betweenness' | 'pagerank' = 'betweenness';

	const W = 900;
	const H = 380;

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

	function drawLegendAndViolin(
		svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
		sizeScale: d3.ScalePower<number, number>,
		threshold?: number
	) {
		const g = svg.append('g').attr('transform', `translate(14, -50)`);

		// title
		g.append('text')
			.attr('x', 0)
			.attr('y', 0)
			.attr('font-size', '12px')
			.attr('font-weight', 500)
			.attr('fill', '#666')
			.text(metric === 'betweenness' ? 'Betweenness' : 'PageRank');

		// outlier legend dot
		g.append('circle').attr('cx', 6).attr('cy', 20).attr('r', 5).attr('fill', '#e03333');
		g.append('text')
			.attr('x', 16)
			.attr('y', 20)
			.attr('dominant-baseline', 'middle')
			.attr('font-size', '10px')
			.attr('fill', '#555')
			.text(threshold != null ? `Outlier (> ${threshold.toFixed(4)})` : 'outlier');

		// size legend
		const domain = sizeScale.domain();
		const mid = (domain[0] + domain[1]) / 2;
		[domain[0], mid, domain[1]].forEach((v, i) => {
			const r = sizeScale(v);
			const x = i * 46 + 6;
			g.append('circle')
				.attr('cx', x)
				.attr('cy', 68 - r)
				.attr('r', r)
				.attr('fill', '#888')
				.attr('fill-opacity', 0.6);
			g.append('text')
				.attr('x', x)
				.attr('y', 80)
				.attr('text-anchor', 'middle')
				.attr('font-size', '9px')
				.attr('fill', '#777')
				.text(['Low', 'Mid', 'High'][i]);
		});

		// Violin + jitter
		const values = fullNet.nodes
			.map((d) => ({ v: d[metric] as number, outlier: isOutlier(d, metric) }))
			.filter((d) => d.v != null);

		const VPAD_TOP = 100; // y-pixel where violin top starts (below legend)
		const VPAD_BOT = 5; // bottom margin inside the SVG
		const violinH = H - VPAD_TOP - VPAD_BOT;
		const cx = 70; // horizontal centre of violin in the legend column
		const halfW = 35; // max half-width of violin body

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
			.attr('stroke-width', 0.8)
			.attr('transform', `translate(-14, 0)`);

		// IQR box
		const sorted = values.map((d) => d.v).sort(d3.ascending);
		const q1 = d3.quantile(sorted, 0.25)!;
		const q3 = d3.quantile(sorted, 0.75)!;
		const med = d3.quantile(sorted, 0.5)!;
		g.append('rect')
			.attr('x', cx - halfW * 0.35 - 14)
			.attr('y', yScale(q3))
			.attr('width', halfW * 0.7)
			.attr('height', yScale(q1) - yScale(q3))
			.attr('fill', '#fff')
			.attr('stroke', '#555')
			.attr('stroke-width', 0.8);
		g.append('line')
			.attr('x1', cx - halfW * 0.35 - 14)
			.attr('x2', cx + halfW * 0.35 - 14)
			.attr('y1', yScale(med))
			.attr('y2', yScale(med))
			.attr('stroke', '#222')
			.attr('stroke-width', 1.5);

		// threshold line
		if (threshold != null) {
			g.append('line')
				.attr('x1', cx - halfW - 14)
				.attr('x2', cx + halfW - 14)
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
				.attr('cx', cx + jitter() - 14)
				.attr('cy', yScale(d.v))
				.attr('r', 1.8)
				.attr('fill', d.outlier ? '#e03333' : '#333')
				.attr('fill-opacity', d.outlier ? 0.9 : 0.25);
		});

		// y-axis (right side of violin)
		const axis = d3.axisRight(yScale).ticks(4).tickFormat(d3.format('.2~e'));
		g.append('g')
			.attr('transform', `translate(${cx + halfW - 14}, 0)`)
			.call(axis)
			.call((ax) => {
				ax.selectAll('text').attr('font-size', '8px').attr('fill', '#888');
				ax.selectAll('line,path').attr('stroke', '#ccc');
			});
	}

	function render() {
		if (!fullNet?.nodes?.length) return;
		simulation?.stop();

		const nodes = fullNet.nodes.map((d) => ({ ...d }));
		const links = fullNet.links.map((d) => ({ ...d }));
		const sizeScale = buildSizeScale(nodes, metric);
		const threshold = getThreshold(metric);

		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();
		svg.attr('viewBox', [0, 0, W, H]).style('background', 'transparent').style('cursor', 'grab');

		const zoomLayer = svg.append('g');
		const zoom = d3
			.zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.15, 6])
			.on('zoom', (e) => zoomLayer.attr('transform', e.transform));
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
			.force('center', d3.forceCenter(W / 2, H / 2))
			.force(
				'collide',
				d3.forceCollide((d: any) => sizeScale(d[metric] ?? 0) + 1)
			);

		simulation.on('tick', () => {
			link
				.attr('x1', (d: any) => d.source.x)
				.attr('y1', (d: any) => d.source.y)
				.attr('x2', (d: any) => d.target.x)
				.attr('y2', (d: any) => d.target.y);
			node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
		});

		node.call(
			d3.drag<any, any>().on('drag', (e, d) => {
				d.fx = e.x;
				d.fy = e.y;
			})
		);

		// legend + violin drawn on top of the zoom layer, pinned to SVG coords
		drawLegendAndViolin(svg, sizeScale, threshold);
	}

	function switchMetric(m: 'betweenness' | 'pagerank') {
		metric = m;
		render();
	}

	$: if (fullNet?.nodes?.length) render();
	onMount(() => render());
	onDestroy(() => simulation?.stop());
</script>

<div
	style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; margin-left: 4px; margin-top: 3px; "
>
	<span style="font-size: 12px; color: #666; margin-left: 4px;">Metric:</span>
	<button
		style="font-size: 12px; padding: 2px 10px; border-radius: 4px; border: 1px solid #bbb;
			background: {metric === 'betweenness' ? '#e03333' : 'transparent'};
			color: {metric === 'betweenness' ? '#fff' : 'inherit'}; cursor: pointer;"
		onclick={() => switchMetric('betweenness')}
	>
		Betweenness
	</button>
	<button
		style="font-size: 12px; padding: 2px 10px; border-radius: 4px; border: 1px solid #bbb;
			background: {metric === 'pagerank' ? '#e03333' : 'transparent'};
			color: {metric === 'pagerank' ? '#fff' : 'inherit'}; cursor: pointer;"
		onclick={() => switchMetric('pagerank')}
	>
		PageRank
	</button>
</div>

<svg bind:this={svgEl} style="width:100%; height:450px;"></svg>
