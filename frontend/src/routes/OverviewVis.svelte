<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { sender, receiver } from '$lib/stores';

	type LRDatum = { sender: string; receiver: string; count: number };

	export let fullNet: {
		nodes: any[];
		links: any[];
		stats?: any;
		celltypes: string[];
		total_nodes: number;
		total_links: number;
		heatmaps: {
			lr_heatmap: {
				data: LRDatum[];
				sender_totals: Record<string, number>;
				receiver_totals: Record<string, number>;
			};
			tfl_heatmap: { data: Record<string, number> };
			rtf_heatmap: { data: Record<string, number> };
		};
	};

	let containerEl: HTMLDivElement;
	let lrSvgEl: SVGSVGElement;
	let tfSvgEl: SVGSVGElement;
	let resizeObserver: ResizeObserver;

	// Live container dimensions — updated by ResizeObserver
	let containerW = 400;
	let containerH = 530;

	const BAR_SIZE = 30;
	const AXIS_LEFT = 88;
	const AXIS_BOT = 88;

	// TF heatmap gets a fixed fraction of total height; LR gets the rest
	const TF_HEIGHT_FRAC = 0.28;

	function getLayout(cts: string[], availableH: number) {
		const totalW = Math.floor(containerW * 0.95);
		const gridW = totalW - AXIS_LEFT - BAR_SIZE - 30;

		const lrHeight = Math.floor(availableH * (1 - TF_HEIGHT_FRAC));
		const availGridH = lrHeight - BAR_SIZE - AXIS_BOT;
		const cellByWidth = Math.floor(gridW / cts.length);
		const cellByHeight = Math.floor(availGridH / cts.length);
		const cellSize = Math.max(4, Math.min(cellByHeight, cellByWidth));

		return { totalW, gridW, cellSize };
	}

	function drawLRHeatmap(availableH: number) {
		if (!lrSvgEl || !fullNet?.heatmaps?.lr_heatmap) return;
		const { data: lrdata, sender_totals, receiver_totals } = fullNet.heatmaps.lr_heatmap;
		const cts = fullNet.celltypes;
		if (!cts?.length || !lrdata?.length) return;

		const { totalW, gridW, cellSize } = getLayout(cts, availableH);
		const gridH = cellSize * cts.length;
		const totalH = BAR_SIZE + gridH + AXIS_BOT;
		const gx = AXIS_LEFT + BAR_SIZE;
		const gy = BAR_SIZE;

		d3.select(lrSvgEl).selectAll('*').remove();
		const svg = d3.select(lrSvgEl).attr('width', totalW).attr('height', totalH);

		const x = d3.scaleBand().domain(cts).range([0, gridW]).padding(0.06);
		const y = d3.scaleBand().domain(cts).range([0, gridH]).padding(0.06);

		const heatColor = d3
			.scaleSequential()
			.domain([0, d3.max(lrdata, (d) => d.count) ?? 1])
			.interpolator(d3.interpolateRgb('#f7fcf0', '#08589e'));

		const g = svg.append('g').attr('transform', `translate(${gx},${gy})`);

		// cells
		g.selectAll<SVGRectElement, LRDatum>('rect.cell')
			.data(lrdata)
			.join('rect')
			.attr('class', 'cell')
			.attr('x', (d) => x(d.receiver)!)
			.attr('y', (d) => y(d.sender)!)
			.attr('width', x.bandwidth())
			.attr('height', y.bandwidth())
			.attr('fill', (d) => heatColor(d.count))
			.style('cursor', 'pointer')
			.on('mouseover', function () {
				d3.select(this).transition().duration(30).attr('opacity', 0.7);
			})
			.on('mouseout', function () {
				d3.select(this).transition().duration(30).attr('opacity', 1);
			})
			.on('click', (_event, d) => {
				sender.set(d.sender);
				receiver.set(d.receiver);
			});

		// cell value labels
		const fontSize = Math.max(6, Math.min(10, x.bandwidth() / 3));
		const maxCount = d3.max(lrdata, (d) => d.count) ?? 1;
		g.selectAll<SVGTextElement, LRDatum>('text.cell-val')
			.data(lrdata.filter((d) => d.count > 0))
			.join('text')
			.attr('class', 'cell-val')
			.attr('x', (d) => x(d.receiver)! + x.bandwidth() / 2)
			.attr('y', (d) => y(d.sender)! + y.bandwidth() / 2)
			.attr('dominant-baseline', 'middle')
			.attr('text-anchor', 'middle')
			.style('font-size', `${fontSize}px`)
			.style('fill', (d) => (d.count > maxCount * 0.6 ? '#fff' : '#333'))
			.style('pointer-events', 'none')
			.text((d) => d.count);

		// x axis — receivers
		g.append('g')
			.attr('transform', `translate(0,${gridH + 3})`)
			.call(d3.axisBottom(x).tickSize(0))
			.call((ax) => ax.select('.domain').remove())
			.selectAll('text')
			.attr('transform', 'rotate(-40)')
			.attr('dy', '0.2em')
			.attr('dx', '-0.6em')
			.style('text-anchor', 'end')
			.style('font-size', '10px');

		// y axis — senders
		g.append('g')
			.attr('transform', `translate(-${BAR_SIZE * 0.2},0)`)
			.call(d3.axisLeft(y).tickSize(0))
			.call((ax) => ax.select('.domain').remove())
			.selectAll('text')
			.style('text-anchor', 'end')
			.style('font-size', '10px');

		// axis titles
		svg
			.append('text')
			.attr('x', gx + gridW / 2)
			.attr('y', totalH - 2)
			.attr('text-anchor', 'middle')
			.style('font-size', '10px')
			.style('fill', '#777')
			.text('RECEIVER');

		svg
			.append('text')
			.attr('transform', 'rotate(-90)')
			.attr('x', -(gy + gridH / 2))
			.attr('y', 10)
			.attr('text-anchor', 'middle')
			.style('font-size', '10px')
			.style('fill', '#777')
			.text('SENDER');

		svg
			.append('text')
			.attr('x', Math.min(60, gx))
			.attr('y', 8)
			.attr('text-anchor', 'middle')
			.style('font-size', '11px')
			.text('LR INTERACTIONS');

		// top bars (receiver totals)
		const maxR = d3.max(Object.values(receiver_totals)) ?? 1;
		const scaleTop = d3.scaleLinear().domain([0, maxR]).range([0, BAR_SIZE - 4]);
		const topG = svg.append('g').attr('transform', `translate(${gx},${gy - BAR_SIZE + 2})`);
		cts.forEach((ct) => {
			const h = scaleTop(receiver_totals[ct] ?? 0);
			topG
				.append('rect')
				.attr('x', x(ct)!)
				.attr('y', BAR_SIZE - 4 - h)
				.attr('width', x.bandwidth())
				.attr('height', h)
				.attr('fill', '#555')
				.attr('rx', 1);
		});

		// right bars (sender totals)
		const maxS = d3.max(Object.values(sender_totals)) ?? 1;
		const scaleRight = d3.scaleLinear().domain([0, maxS]).range([0, BAR_SIZE - 4]);
		const rightG = svg.append('g').attr('transform', `translate(${gx + gridW + 4},${gy})`);
		cts.forEach((ct) => {
			rightG
				.append('rect')
				.attr('x', 0)
				.attr('y', y(ct)!)
				.attr('width', scaleRight(sender_totals[ct] ?? 0))
				.attr('height', y.bandwidth())
				.attr('fill', '#555')
				.attr('rx', 1);
		});
	}

	function drawTFHeatmap(availableH: number) {
		if (!tfSvgEl || !fullNet?.heatmaps) return;
		const tfldata = fullNet.heatmaps.tfl_heatmap.data;
		const rtfdata = fullNet.heatmaps.rtf_heatmap.data;
		const cts = fullNet.celltypes;
		if (!cts?.length) return;

		const { totalW, gridW } = getLayout(cts, availableH);

		// ROW_H derived from the TF fraction of total container height
		const tfTotalH = Math.floor(availableH * TF_HEIGHT_FRAC);
		const ROW_H = Math.max(12, Math.floor((tfTotalH - BAR_SIZE - AXIS_BOT) / 2));
		const N_ROWS = 2;
		const gridH = ROW_H * N_ROWS;
		const gx = AXIS_LEFT + BAR_SIZE;
		const gy = BAR_SIZE;
		const totalH = gy + gridH + AXIS_BOT;

		d3.select(tfSvgEl).selectAll('*').remove();
		const svg = d3.select(tfSvgEl).attr('width', totalW).attr('height', totalH);

		const x = d3.scaleBand().domain(cts).range([0, gridW]).padding(0.06);
		const rows = ['TFL', 'RTF'];
		const y = d3.scaleBand().domain(rows).range([0, gridH]).padding(0.06);

		const allVals = [...cts.map((ct) => tfldata[ct] ?? 0), ...cts.map((ct) => rtfdata[ct] ?? 0)];
		const maxVal = d3.max(allVals) ?? 1;
		const heatColor = d3
			.scaleSequential()
			.domain([0, maxVal])
			.interpolator(d3.interpolateRgb('#f7fcf0', '#08589e'));

		const g = svg.append('g').attr('transform', `translate(${gx},${gy})`);
		const labelFontSize = Math.max(6, Math.min(10, x.bandwidth() / 3));

		(['TFL', 'RTF'] as const).forEach((rowKey) => {
			const rowData = rowKey === 'TFL' ? tfldata : rtfdata;
			cts.forEach((ct) => {
				const val = rowData[ct] ?? 0;
				g.append('rect')
					.attr('x', x(ct)!)
					.attr('y', y(rowKey)!)
					.attr('width', x.bandwidth())
					.attr('height', y.bandwidth())
					.attr('fill', heatColor(val));
				if (val > 0) {
					g.append('text')
						.attr('x', x(ct)! + x.bandwidth() / 2)
						.attr('y', y(rowKey)! + y.bandwidth() / 2)
						.attr('dominant-baseline', 'middle')
						.attr('text-anchor', 'middle')
						.style('font-size', `${labelFontSize}px`)
						.style('fill', val > maxVal * 0.6 ? '#fff' : '#333')
						.style('pointer-events', 'none')
						.text(val);
				}
			});
		});

		// x axis
		g.append('g')
			.attr('transform', `translate(0,${gridH + 3})`)
			.call(d3.axisBottom(x).tickSize(0))
			.call((ax) => ax.select('.domain').remove())
			.selectAll('text')
			.attr('transform', 'rotate(-40)')
			.attr('dy', '0.2em')
			.attr('dx', '-0.6em')
			.style('text-anchor', 'end')
			.style('font-size', '10px');

		// y axis
		g.append('g')
			.attr('transform', `translate(-${BAR_SIZE * 0.2},0)`)
			.call(d3.axisLeft(y).tickSize(0))
			.call((ax) => ax.select('.domain').remove())
			.selectAll('text')
			.style('text-anchor', 'end')
			.style('font-size', '10px');

		svg
			.append('text')
			.attr('x', Math.min(15, gx))
			.attr('y', 9)
			.attr('text-anchor', 'start')
			.style('font-size', '11px')
			.text('TF INTERACTIONS');

		// svg
		// 	.append('text')
		// 	.attr('x', Math.max(60, gx - gridW / 5))
		// 	.attr('y', 9)
		// 	.attr('text-anchor', 'start')
		// 	.style('font-size', '10px')
		// 	.style('fill', '#777')
		// 	.text('CELL TYPE');
	}

	function drawAll() {
		if (!fullNet?.celltypes?.length || containerW === 0 || containerH === 0) return;
		// Reserve a small gap between the two SVGs
		const GAP = 12;
		drawLRHeatmap(containerH - GAP);
		drawTFHeatmap(containerH - GAP);
	}

	$: if (fullNet?.celltypes?.length) drawAll();

	onMount(() => {
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				if (width > 0 && height > 0) {
					containerW = width;
					containerH = height;
					drawAll();
				}
			}
		});
		resizeObserver.observe(containerEl);
		if (fullNet?.celltypes?.length) drawAll();
	});

	onDestroy(() => resizeObserver?.disconnect());
</script>

<div
	bind:this={containerEl}
	style="display:flex; flex-direction:column; align-items:center; gap:0; width:100%; height:100%; padding:0.5rem 0; overflow:hidden;"
>
	<svg bind:this={lrSvgEl}></svg>
	<svg bind:this={tfSvgEl}></svg>
</div>