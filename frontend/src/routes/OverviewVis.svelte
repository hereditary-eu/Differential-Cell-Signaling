<script lang="ts">
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { sender, receiver } from '$lib/stores'
  
  interface NetworkStats {
		nNodes: number;
		nLigands: number;
		nReceptors: number;
		nTFs: number;
		nLinks: number;
		nLRLinks: number;
		nTFLLinks: number;
		nRTFLinks: number;
	}
  type LRDatum = { sender: string; receiver: string; count: number };

  type FullNet = {
    nodes: unknown[];
    links: unknown[];
    stats: NetworkStats;
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

  export let fullNet: FullNet;
	
  let containerEl: HTMLDivElement;
  let lrSvgEl:    SVGSVGElement;
  // let tfSvgEl: SVGSVGElement;
  function getContainerWidth(): number {
    return containerEl?.clientWidth ?? 400;
  }

  function drawLRHeatmap() {
    if (!lrSvgEl || !fullNet?.heatmaps?.lr_heatmap) return;
    const { data, sender_totals, receiver_totals } = fullNet.heatmaps.lr_heatmap;
    const cts = fullNet.celltypes;
    if (!cts?.length || !data?.length) return;

    d3.select(lrSvgEl).selectAll('*').remove();

    const totalW   = Math.floor(getContainerWidth() * 0.85);
    const barSize  = 30;           // top / right bar thickness
    const axisLeft = 88;           // room for sender labels (y-axis)
    const axisBot  = 88;           // room for receiver labels (x-axis)
    const gridW    = totalW - axisLeft - barSize - 30;
    const cellSize = Math.floor(gridW / cts.length);
    const gridH    = cellSize * cts.length;
    const totalH   = barSize + gridH + axisBot;

    const svg = d3.select(lrSvgEl)
      .attr('width',  totalW)
      .attr('height', totalH);

    // grid origin
    const gx = axisLeft + barSize;
    const gy = barSize;

    const x = d3.scaleBand().domain(cts).range([0, gridW]).padding(0.06);
    const y = d3.scaleBand().domain(cts).range([0, gridH]).padding(0.06);

    const heatColor = d3.scaleSequential()
      .domain([0, d3.max(data, d => d.count) ?? 1])
      .interpolator(d3.interpolateRgb('#f7fcf0', '#08589e'));

    const g = svg.append('g').attr('transform', `translate(${gx},${gy})`);

    // cells
    g.selectAll<SVGRectElement, (typeof data)[0]>('rect.cell')
      .data(data)
      .join('rect')
      .attr('class',  'cell')
      .attr('x',      d => x(d.receiver)!)
      .attr('y',      d => y(d.sender)!)
      .attr('width',  x.bandwidth())
      .attr('height', y.bandwidth())
      .attr('fill',   d => heatColor(d.count))
      .on('click', (event: any, d: {sender: string, receiver: string, count: number}) => {
        sender.set(d.sender);
        receiver.set(d.receiver);
      });

    // cell value labels
    const fontSize = Math.max(6, Math.min(10, x.bandwidth() / 3));
    g.selectAll<SVGTextElement, (typeof data)[0]>('text.cell-val')
      .data(data.filter(d => d.count > 0))
      .join('text')
      .attr('class', 'cell-val')
      .attr('x', d => x(d.receiver)! + x.bandwidth() / 2)
      .attr('y', d => y(d.sender)!   + y.bandwidth() / 2)
      .attr('dominant-baseline', 'middle')
      .attr('text-anchor', 'middle')
      .style('font-size', `${fontSize}px`)
      .style('fill', d => d.count > (d3.max(data, d => d.count) ?? 1) * 0.6 ? '#fff' : '#333')
      .style('pointer-events', 'none')
      .text(d => d.count);

    // x axis — receivers 
    g.append('g')
      .attr('transform', `translate(0,${gridH + 3})`)
      .call(d3.axisBottom(x).tickSize(0))
      .call(ax => ax.select('.domain').remove())
      .selectAll('text')
      .attr('transform', 'rotate(-40)')
      .attr('dy', '0.2em')
      .attr('dx', '-0.6em')
      .style('text-anchor', 'end')
      .style('font-size', '10px');

    // y axis — senders 
    g.append('g')
      .attr('transform', `translate(-${barSize *0.2},0)`)
      .call(d3.axisLeft(y).tickSize(0))
      .call(ax => ax.select('.domain').remove())
      .selectAll('text')
      .style('text-anchor', 'end')
      .style('font-size', '10px');

    // axis titles 
    svg.append('text')
      .attr('x', gx + gridW / 2)
      .attr('y', totalH - 2)
      .attr('text-anchor', 'middle')
      .style('font-size', '10px').style('fill', '#777')
      .text('RECEIVER');

    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(gy + gridH / 2))
      .attr('y', 10)                    // 10px from left edge
      .attr('text-anchor', 'middle')
      .style('font-size', '10px').style('fill', '#777')
      .text('SENDER');

    svg.append('text')
        .attr('x', gx - gridW / 5)
        .attr('y', 8)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .text('LR INTERACTIONS');
    
    // top bars
    const maxR    = d3.max(Object.values(receiver_totals)) ?? 1;
    const scaleTop = d3.scaleLinear().domain([0, maxR]).range([0, barSize - 4]);
    const topG    = svg.append('g').attr('transform', `translate(${gx},${gy - barSize + 2})`);
    cts.forEach(ct => {
      const h = scaleTop(receiver_totals[ct] ?? 0);
      topG.append('rect')
        .attr('x',      x(ct)!)
        .attr('y',      barSize - 4 - h)
        .attr('width',  x.bandwidth())
        .attr('height', h)
        .attr('fill',   '#555').attr('rx', 1);
    });

    // right bars 
    const maxS     = d3.max(Object.values(sender_totals)) ?? 1;
    const scaleRight = d3.scaleLinear().domain([0, maxS]).range([0, barSize - 4]);
    const rightG   = svg.append('g')
      .attr('transform', `translate(${gx + gridW + 4},${gy})`);
    cts.forEach(ct => {
      rightG.append('rect')
        .attr('x',      0)
        .attr('y',      y(ct)!)
        .attr('width',  scaleRight(sender_totals[ct] ?? 0))
        .attr('height', y.bandwidth())
        .attr('fill',   '#555').attr('rx', 1);
    });
  }
  function drawTFHeatmap() {

  }
  function drawAll() {
    drawLRHeatmap();
  }

  $: if (fullNet?.celltypes?.length) drawAll();

  onMount(() => {
    if (fullNet?.celltypes?.length) drawAll();
  });
</script>

<div bind:this={containerEl} style="display:flex; gap:1%; flex-wrap:nowrap; width:100%; padding:0.5rem 0;">
  <svg bind:this={lrSvgEl}></svg>
</div>