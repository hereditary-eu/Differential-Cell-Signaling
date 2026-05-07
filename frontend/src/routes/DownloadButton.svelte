<script lang="ts">
	export let getSvgEl: () => SVGSVGElement | null;
	export let getLegendEl: () => HTMLElement | null;
	export let filename: string = 'diffCellSig';

	let exporting = false;
	let formatMenuOpen = false;

	async function buildComposedSvg(): Promise<SVGSVGElement> {
		const svgEl = getSvgEl();
		if (!svgEl) throw new Error('No SVG element');
		// Deep clone the network SVG
		const clone = svgEl.cloneNode(true) as SVGSVGElement;

		// Ensure white background rect for export
		const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
		bgRect.setAttribute('width', '100%');
		bgRect.setAttribute('height', '100%');
		bgRect.setAttribute('fill', 'white');
		clone.insertBefore(bgRect, clone.firstChild);

		// Pull in global defs (markers) from the document-level hidden SVG
		const globalDefs = document.querySelector('svg > defs');
		if (globalDefs) {
			let cloneDefs = clone.querySelector('defs');
			if (!cloneDefs) {
				cloneDefs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
				clone.insertBefore(cloneDefs, clone.firstChild);
			}
			cloneDefs.innerHTML += globalDefs.innerHTML;
		}
		// Embed legend as a foreignObject
		const legendEl = getLegendEl();
		if (legendEl) {
			const legendRect = legendEl.getBoundingClientRect();
			const svgRect = svgEl.getBoundingClientRect();
			// Compute legend position relative to the SVG
			const vb = svgEl.viewBox.baseVal;
			const scaleX = vb.width / svgRect.width;
			const scaleY = vb.height / svgRect.height;
			const relX = (legendRect.left - svgRect.left) * scaleX;
			const relY = (legendRect.top - svgRect.top) * scaleY;
			const lW = legendRect.width * scaleX;
			const lH = legendRect.height * scaleY;

			const fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
			fo.setAttribute('x', String(Math.max(0, relX)));
			fo.setAttribute('y', String(Math.max(0, relY)));
			fo.setAttribute('width', String(lW));
			fo.setAttribute('height', String(lH));

			const div = document.createElement('div');
			div.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
			div.innerHTML = legendEl.outerHTML;
			inlineStyles(div, legendEl);
			fo.appendChild(div);
			clone.appendChild(fo);
		}
		return clone;
	}
	function inlineStyles(cloneNode: Element, sourceNode: Element) {
		const computed = window.getComputedStyle(sourceNode);
		const relevant = [
			'font-size',
			'font-family',
			'font-weight',
			'color',
			'background-color',
			'border',
			'border-radius',
			'padding',
			'display',
			'flex-direction',
			'align-items',
			'gap',
			'line-height',
			'white-space'
		];
		let style = '';
		for (const prop of relevant) {
			const val = computed.getPropertyValue(prop);
			if (val) style += `${prop}:${val};`;
		}
		(cloneNode as HTMLElement).style?.cssText
			? ((cloneNode as HTMLElement).style.cssText = style)
			: cloneNode.setAttribute('style', style);

		const cloneChildren = cloneNode.children;
		const sourceChildren = sourceNode.children;
		for (let i = 0; i < Math.min(cloneChildren.length, sourceChildren.length); i++) {
			inlineStyles(cloneChildren[i], sourceChildren[i]);
		}
	}

	function svgToString(svgEl: SVGSVGElement): string {
		const serializer = new XMLSerializer();
		return serializer.serializeToString(svgEl);
	}

	async function svgToBlobUrl(svgEl: SVGSVGElement): Promise<string> {
		const str = svgToString(svgEl);
		const blob = new Blob([str], { type: 'image/svg+xml;charset=utf-8' });
		return URL.createObjectURL(blob);
	}

	async function svgToCanvas(svgEl: SVGSVGElement, scale = 3): Promise<HTMLCanvasElement> {
		const vb = svgEl.viewBox.baseVal;
		const w = vb.width || svgEl.clientWidth || 800;
		const h = vb.height || svgEl.clientHeight || 600;

		const url = await svgToBlobUrl(svgEl);
		return new Promise((resolve, reject) => {
			const img = new Image();
			img.onload = () => {
				const canvas = document.createElement('canvas');
				canvas.width = w * scale;
				canvas.height = h * scale;
				const ctx = canvas.getContext('2d')!;
				ctx.fillStyle = 'white';
				ctx.fillRect(0, 0, canvas.width, canvas.height);
				ctx.scale(scale, scale);
				ctx.drawImage(img, 0, 0, w, h);
				URL.revokeObjectURL(url);
				resolve(canvas);
			};
			img.onerror = reject;
			img.src = url;
		});
	}

	async function downloadSvg() {
		const composed = await buildComposedSvg();
		const str = svgToString(composed);
		const blob = new Blob([str], { type: 'image/svg+xml;charset=utf-8' });
		triggerDownload(URL.createObjectURL(blob), `${filename}.svg`);
	}

	async function downloadPng() {
		const composed = await buildComposedSvg();
		const canvas = await svgToCanvas(composed, 3);
		canvas.toBlob((blob) => {
			if (blob) triggerDownload(URL.createObjectURL(blob), `${filename}.png`);
		}, 'image/png');
	}
	async function handleExport(format: 'svg' | 'png') {
		formatMenuOpen = false;
		exporting = true;
		try {
			if (format === 'svg') await downloadSvg();
			else await downloadPng();
		} catch (err) {
			console.error('Export failed:', err);
		} finally {
			exporting = false;
		}
	}

	function triggerDownload(url: string, name: string) {
		const a = document.createElement('a');
		a.href = url;
		a.download = name;
		a.click();
		setTimeout(() => URL.revokeObjectURL(url), 2000);
	}
</script>

<div style="position: relative; display: inline-block;">
	<button
		onclick={() => (formatMenuOpen = !formatMenuOpen)}
		disabled={exporting}
		style="
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            font-size: 11px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: white;
            cursor: {exporting ? 'wait' : 'pointer'};
            opacity: {exporting ? 0.6 : 1};
        "
		title="Export image"
	>
		{#if exporting}
			<svg
				width="12"
				height="12"
				viewBox="0 0 12 12"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
			>
				<circle cx="6" cy="6" r="4.5" stroke-dasharray="14" stroke-dashoffset="0">
					<animateTransform
						attributeName="transform"
						type="rotate"
						from="0 6 6"
						to="360 6 6"
						dur="0.8s"
						repeatCount="indefinite"
					/>
				</circle>
			</svg>
		{:else}
			<svg
				width="12"
				height="12"
				viewBox="0 0 12 12"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
			>
				<path d="M6 1v7M3 5.5l3 3 3-3M2 10h8" />
			</svg>
		{/if}
		Export
	</button>

	{#if formatMenuOpen}
		<div
			style="
            position: absolute;
            top: calc(100% + 4px);
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            z-index: 100;
            min-width: 90px;
            overflow: hidden;
        "
		>
			{#each ['svg', 'png'] as fmt}
				<button
					onclick={() => handleExport(fmt as any)}
					style="
                        display: block;
                        width: 100%;
                        padding: 6px 12px;
                        font-size: 11px;
                        text-align: left;
                        background: none;
                        border: none;
                        cursor: pointer;
                        text-transform: uppercase;
                        letter-spacing: 0.04em;
                        color: #333;
                    "
					onmouseenter={(e) => ((e.currentTarget as HTMLElement).style.background = '#f5f5f5')}
					onmouseleave={(e) => ((e.currentTarget as HTMLElement).style.background = 'none')}
				>
					{fmt}
				</button>
			{/each}
		</div>
	{/if}
</div>
