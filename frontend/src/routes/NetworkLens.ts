/**
 * NetworkLens.ts
 *
 * Self-contained magnifying-lens overlay for an SVG force-directed graph.
 * Has zero dependency on Svelte reactivity – it is plain TypeScript + D3.
 *
 * Usage
 * -----
 *   const lens = new NetworkLens(svg, { radius: 80, zoom: 3.5, metric: 'pagerank' });
 *
 *   // Call once after svg.selectAll('*').remove() recreates the DOM:
 *   lens.mount(svg);
 *
 *   // Keep in sync with the D3 zoom transform:
 *   lens.setZoomTransform(e.transform);
 *
 *   // Keep in sync with simulation data (same array objects D3 mutates):
 *   lens.setData(nodes, links);
 *
 *   // Enable / disable the lens (e.g. from a button):
 *   lens.setEnabled(true);
 *
 *   // Call on every simulation tick while the lens is active:
 *   lens.refreshIfActive(sizeScale);
 *
 *   // Destroy mouse listeners when the SVG is torn down:
 *   lens.destroy();
 */

import * as d3 from 'd3';

export interface LensOptions {
	radius?: number;
	zoom?: number;
	metric?: 'betweenness' | 'pagerank';
}

type SvgSel  = d3.Selection<SVGSVGElement, unknown, null, undefined>;
type GSel     = d3.Selection<SVGGElement,   unknown, null, undefined>;

export class NetworkLens {
	private R:      number;
	private MAG:    number;
	metric: 'betweenness' | 'pagerank';

	private enabled  = false;
	private active   = false;   // true while mouse is inside the SVG
	private posX     = 0;
	private posY     = 0;
	private rafId: number | null = null;
	private svgW     = 900;     // updated via setSvgSize()
	private svgH     = 380;

	// ── D3 data refs 
	private nodes: any[] = [];
	private links: any[] = [];
	private zoomT: d3.ZoomTransform = d3.zoomIdentity;

	// ── DOM refs (rebuilt on each mount()) ───────────────────────────────────
	private group:    GSel | null = null;
	private content:  GSel | null = null;
	private svgEl:    SVGSVGElement | null = null;

	constructor(options: LensOptions = {}) {
		this.R      = options.radius ?? 70;
		this.MAG    = options.zoom   ?? 3.5;
		this.metric = options.metric ?? 'pagerank';
	}

	/** Re-mount after the SVG has been wiped and redrawn. */
	mount(svg: SvgSel, svgEl: SVGSVGElement): void {
		this.svgEl = svgEl;
		this.active = false;
		this.group  = null;
		this.content = null;

		this._buildDOM(svg);
		this._bindEvents(svg);
	}

	setZoomTransform(t: d3.ZoomTransform): void { this.zoomT = t; }
	setData(nodes: any[], links: any[]): void    { this.nodes = nodes; this.links = links; }
	setSvgSize(w: number, h: number): void       { this.svgW = w; this.svgH = h; }

	setEnabled(on: boolean): void {
		this.enabled = on;
		if (!on) {
			this.active = false;
			this.group?.style('display', 'none');
			if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
		}
	}

	/** Call from the simulation tick handler. */
	refreshIfActive(sizeScale: d3.ScalePower<number, number>): void {
		if (this.active && this.enabled) this._draw(this.posX, this.posY, sizeScale);
	}

	/** Remove mouse listeners (call from onDestroy). */
	destroy(): void {
		if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
		// d3 event listeners are removed automatically when the SVG is wiped on re-render
	}

	private _buildDOM(svg: SvgSel): void {
		const R = this.R;

		// Ensure <defs> exists and add the clip-path (local coords: 0,0 = lens centre)
		const defs: d3.Selection<SVGDefsElement, unknown, null, undefined> =
			svg.select<SVGDefsElement>('defs').empty()
				? svg.append<SVGDefsElement>('defs')
				: svg.select<SVGDefsElement>('defs');

		defs.append('clipPath')
			.attr('id', 'lens-clip')
			.append('circle')
			.attr('r', R)
			.attr('cx', 0).attr('cy', 0);

		const g = svg.append('g').attr('class', 'lens-group').style('display', 'none');
		this.group = g;

        g.append('circle').attr('r', R)
			.attr('fill', 'rgba(255,255,255,0.82)').attr('stroke', 'none');

		// Clipped content layer
		this.content = g.append('g').attr('clip-path', 'url(#lens-clip)');
		this.content.append('g').attr('class', 'lens-links');
		this.content.append('g').attr('class', 'lens-nodes');
		this.content.append('g').attr('class', 'lens-labels');

		// Decorative ring (drawn on top of content so it isn't clipped)
		g.append('circle').attr('r', R)
			.attr('fill', 'none')
			.attr('stroke', '#000000a8').attr('stroke-width', 1.5)
			.attr('stroke-dasharray', '4,3');

		g.append('line')
			.attr('x1', -R).attr('x2', R).attr('y1', 0).attr('y2', 0)
			.attr('stroke', '#93c5fd').attr('stroke-width', 0.5).attr('stroke-opacity', 0.6);
		g.append('line')
			.attr('x1', 0).attr('x2', 0).attr('y1', -R).attr('y2', R)
			.attr('stroke', '#93c5fd').attr('stroke-width', 0.5).attr('stroke-opacity', 0.6);
	}

	private _bindEvents(svg: SvgSel): void {
		svg.on('mousemove.lens', (e: MouseEvent) => {
			if (!this.enabled || !this.group) return;
			const pt = this._svgPoint(e);
			this.posX = pt.x;
			this.posY = pt.y;
			if (!this.active) {
				this.active = true;
				this.group.style('display', null);
			}
			if (this.rafId) cancelAnimationFrame(this.rafId);
			this.rafId = requestAnimationFrame(() => {
				// sizeScale is not available here _draw is called from refreshIfActive
				// if the sim has cooled down call it with the last-known scale.
				if (this._lastSizeScale) this._draw(this.posX, this.posY, this._lastSizeScale);
				this.rafId = null;
			});
		});

		svg.on('mouseleave.lens', () => {
			this.active = false;
			this.group?.style('display', 'none');
			if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
		});
	}

	// Stored so mousemove rAF can call _draw even after the sim has cooled.
	private _lastSizeScale: d3.ScalePower<number, number> | null = null;

	setSizeScale(s: d3.ScalePower<number, number>): void { this._lastSizeScale = s; }

	private _svgPoint(e: MouseEvent): { x: number; y: number } {
		const el = this.svgEl!;
		const rect = el.getBoundingClientRect();
		return {
			x: (e.clientX - rect.left) * (this.svgW / rect.width),
			y: (e.clientY - rect.top)  * (this.svgH / rect.height)
		};
	}

	private _isOutlier(d: any): boolean {
		return this.metric === 'betweenness' ? d.is_outlier_b : d.is_outlier_p;
	}

	private _draw(svgX: number, svgY: number, sizeScale: d3.ScalePower<number, number>): void {
		if (!this.group || !this.content) return;
		this._lastSizeScale = sizeScale;

		this.group.attr('transform', `translate(${svgX},${svgY})`);

		const t      = this.zoomT;
		const simCx  = (svgX - t.x) / t.k;
		const simCy  = (svgY - t.y) / t.k;
		const simR   = this.R / t.k;
		const simR2  = simR * simR * 1.15;   // slight margin for partial nodes

		const inside = this.nodes.filter((d: any) => {
			const dx = (d.x ?? 0) - simCx;
			const dy = (d.y ?? 0) - simCy;
			return dx * dx + dy * dy <= simR2;
		});
		const insideIds = new Set<any>(inside.map((d: any) => d.id));

		const toL = (sx: number, sy: number) => ({
			lx: (sx - simCx) * t.k * this.MAG,
			ly: (sy - simCy) * t.k * this.MAG
		});

		const insideLinks = this.links.filter(
			(l: any) =>
				insideIds.has(l.source?.id ?? l.source) &&
				insideIds.has(l.target?.id ?? l.target)
		);

		const linkSel = this.content.select<SVGGElement>('.lens-links')
			.selectAll<SVGLineElement, any>('line')
			.data(insideLinks, (d: any) =>
				`${d.source?.id ?? d.source}-${d.target?.id ?? d.target}`
			);

		linkSel.enter().append('line')
			.attr('stroke', '#bbb').attr('stroke-width', 0.8).attr('stroke-opacity', 0.7)
			.merge(linkSel as any)
			.each(function(d: any) {
				const s  = toL(d.source?.x ?? 0, d.source?.y ?? 0);
				const tg = toL(d.target?.x ?? 0, d.target?.y ?? 0);
				d3.select(this)
					.attr('x1', s.lx).attr('y1', s.ly)
					.attr('x2', tg.lx).attr('y2', tg.ly);
			});
		linkSel.exit().remove();

		const nodeSel = this.content.select<SVGGElement>('.lens-nodes')
			.selectAll<SVGCircleElement, any>('circle')
			.data(inside, (d: any) => d.id);

		nodeSel.enter().append('circle')
			.merge(nodeSel as any)
			.each((d: any, i, els) => {
				const { lx, ly } = toL(d.x ?? 0, d.y ?? 0);
				d3.select(els[i])
					.attr('cx', lx).attr('cy', ly)
					.attr('r',  Math.max(4, sizeScale(d[this.metric] ?? 0) * 1.6))
					.attr('fill',         this._isOutlier(d) ? '#e03333' : '#6b8cba')
					.attr('fill-opacity', 0.88)
					.attr('stroke',       this._isOutlier(d) ? '#900'    : '#3a5a80')
					.attr('stroke-width', 1);
			});
		nodeSel.exit().remove();

		const labelSel = this.content.select<SVGGElement>('.lens-labels')
			.selectAll<SVGGElement, any>('g.lens-label')
			.data(inside, (d: any) => d.id);

		const entered = labelSel.enter().append('g').attr('class', 'lens-label')
			.attr('pointer-events', 'none');
		entered.append('text').attr('class', 'ln');
		entered.append('text').attr('class', 'lm');

		entered.merge(labelSel as any).each((d: any, i, els) => {
			const { lx, ly } = toL(d.x ?? 0, d.y ?? 0);
			const r    = Math.max(4, sizeScale(d[this.metric] ?? 0) * 1.6);
			const g    = d3.select(els[i]).attr('transform', `translate(${lx},${ly})`);
			const val  = (d[this.metric] ?? 0) as number;

			g.select('text.ln')
				.attr('y', r + 9).attr('text-anchor', 'middle')
				.attr('font-size', '7px').attr('font-family', 'monospace')
				.attr('font-weight', '700').attr('fill', '#222')
				.text(d.name ?? '');

			g.select('text.lm')
				.attr('y', r + 18).attr('text-anchor', 'middle')
				.attr('font-size', '8px').attr('font-family', 'sans-serif')
				.attr('fill', '#060606')
				.text(`${d.celltype ?? ''}\n${d.moltype ?? ''}`);//\n${val.toExponential(2)}`);
		});
		labelSel.exit().remove();
	}
}