// define here the common variables and functions for network visualizations
import * as d3 from 'd3';

const NODE_SIZES = {
	TF: { base: 7, highlight: 12 },
	ligand: { base: 90, highlight: 200 },
	receptor: { base: 12, highlight: 18 }
};

export function drawNode(
    selection: d3.Selection<any, any, any, any>,
    colorScale: d3.ScaleOrdinal<string, string, string>,
    color: boolean,
    nodeSize = NODE_SIZES
) {
		selection.each(function (d: any) {
			const g = d3.select(this);
			if (d.moltype === 'TF') {
				g.append('circle').attr('r', nodeSize.TF.base).attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			} else if (d.moltype === 'ligand') {
				g.append('path')
					.attr('d', d3.symbol().type(d3.symbolTriangle).size(nodeSize.ligand.base))
					.attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			} else if (d.moltype === 'receptor') {
				g.append('rect')
					.attr('x', -nodeSize.receptor.base / 2)
					.attr('y', -nodeSize.receptor.base / 2)
					.attr('width', nodeSize.receptor.base)
					.attr('height', nodeSize.receptor.base)
					.attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			}
		});
	}

// interpolateViridis wants values between 0 and 1 -> do minmax scale
// TODO in the future, now assuming scSeqComm output: [-1,1]
export function aesEdge(
    selection: d3.Selection<any, any, any, any>,
    aesLRMapping: 'reset' | 'viridis' | 'volcano',
    aesTFMapping: 'reset' | 'endShape'
) {
    selection.attr('stroke', '#999').attr('opacity', 0.9).attr('marker-end', null)
    const lrEdges = selection.filter((d: any) => d.type === 'LR');
    if (aesLRMapping === 'viridis') {
        lrEdges.attr('stroke', (d: any) => d3.interpolateViridis((d.weight + 1) / 2)) // assuming [-1,1]
    } else if (aesLRMapping === 'volcano') {
        lrEdges.attr('stroke', (d: any) => (d.weight < 0 ? '#2166ac' : '#b2182b')) // blue for under-activation //'#8B0000'); // darkred for over-activation
    }     
    if (aesTFMapping === 'endShape') {
        selection.filter((d: any) => d.type === 'TFL').attr('marker-end', (d: any) => d.weight < 0 ? 'url(#Tblunt)' : 'url(#arrow)')
    }    
}

export function updateNodeColors(nodeSelection: d3.Selection<any, any, any, any>, colorScale: d3.ScaleOrdinal<string, string, string>, aesSettings: any) {
		if (!nodeSelection) return;
		nodeSelection.each(function (this: any, d: any) {
			const g = d3.select(this as Element);
			const fill = aesSettings.CT ? colorScale(d.celltype) : '#a9a9a9';
			g.select('circle, path, rect').attr('fill', fill);
		});
	}
export function updateEdgesAes(linkSelection: d3.Selection<any, any, any, any>, aesSettings: any) {
		if (!linkSelection) return;
		linkSelection.call((sel: any) => aesEdge(sel, aesSettings.LR, aesSettings.TF));
	}
// export function to be called when a node is CLICKED (it's not related to sidebarSearch)
export function highlightNode(selectedId: string, links: any, node: d3.Selection<any, any, any, any>, link: d3.Selection<any, any, any, any>) {
        const adjacency: Record<string, Set<string>> = {};
        links.forEach((l: any) => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            adjacency[sourceId] = adjacency[sourceId] || new Set<string>();
            adjacency[targetId] = adjacency[targetId] || new Set<string>();
            adjacency[sourceId].add(targetId);
            adjacency[targetId].add(sourceId);
        });
        function getNeighbors(id: string) {
            return adjacency[id] || new Set<string>();
        }
        const neighbors = getNeighbors(selectedId);

        node.attr('opacity', (d: any) => (d.id === selectedId || neighbors.has(d.id) ? 1 : 0.3));
        link.attr('opacity', (l: any) =>
            l.source.id === selectedId || l.target.id === selectedId ? 1 : 0.1
        );
    }

// export function trimPath(source: { x: number; y: number }, target: { x: number; y: number }, r = 12) {
// 			const dx = target.x - source.x;
// 			const dy = target.y - source.y;
// 			const dist = Math.sqrt(dx * dx + dy * dy);

// 			const ratio = (dist - r) / dist;

// 			return {
// 				x: source.x + dx * ratio,
// 				y: source.y + dy * ratio
// 			};
// 		}
export function trimPath(
    source: { x: number; y: number },
    target: { x: number; y: number },
    r = 9
) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist <= r) return { x: target.x, y: target.y };
    const ratio = (dist - r) / dist;
    return {
        x: source.x + dx * ratio,
        y: source.y + dy * ratio
    };
}

export function defineMarkers(
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>) {
        const defs = svg.append('defs');
		defs
			.append('marker')
			.attr('id', 'arrow')
			.attr('viewBox', '0 -5 10 10')
			.attr('refX', 9)
			.attr('refY', 0)
			.attr('markerWidth', 6)
			.attr('markerHeight', 6)
			.attr('orient', 'auto')
			.append('path')
			.attr('d', 'M0,-5L10,0L0,5')
			.attr('fill', '#999');
		defs
			.append('marker')
			.attr('id', 'Tblunt')
			.attr('viewBox', '-2 -6 4 12')
			.attr('refX', 1)
			.attr('refY', 0)
			.attr('markerWidth', 10)
			.attr('markerHeight', 10)
			.attr('orient', 'auto')
			.append('path')
			.attr('d', 'M0,-6L0,6')
			.attr('stroke', '#999')
			.attr('stroke-width', 2);
    }

export function resetNodesSize (nodeSelection: any, nodeSize = NODE_SIZES) {
    nodeSelection.select('circle').attr('r', nodeSize.TF.base);
    nodeSelection.selectAll('rect')
            .attr('width', nodeSize.receptor.base)
            .attr('height', nodeSize.receptor.base)
            .attr('x', -nodeSize.receptor.base/2)
            .attr('y', -nodeSize.receptor.base/2);
    nodeSelection.selectAll('path')
        .attr('d', d3.symbol().type(d3.symbolTriangle).size(nodeSize.ligand.base));
    return;
}
//this is the highlight called when node is searched by SidebarSearch
export function applyHighlightSearch(
    value: string | null, 
    nodeSelection: any, 
    linkSelection: any, 
    networkData: any,
    nodeSize = NODE_SIZES
) {
		if (!nodeSelection) return;
		if (!value) { //reset
			nodeSelection.attr('opacity', 1);
			linkSelection?.attr('opacity', 1);
            resetNodesSize(nodeSelection, nodeSize);
            return;
		}

		let matchIds: Set<string>;
		if (value.startsWith('name:')) {
			const name = value.slice(5);
			matchIds = new Set(
				(networkData?.nodes ?? []).filter((n: any) => n.name === name).map((n: any) => n.id)
			);
		} else {
			matchIds = new Set(
				(networkData?.nodes ?? []).filter((n: any) => n.verbose_id === value).map((n: any) => n.id)
			);
		}
		nodeSelection.attr('opacity', (d: any) => (matchIds.has(d.id) ? 1 : 0.15));
		linkSelection?.attr('opacity', 0.15);

		nodeSelection.each(function (this: SVGGElement, d: any) {
            const g = d3.select(this);
            const isMatch = matchIds.has(d.id);
            if (d.moltype === 'TF') {
                g.select('circle').attr('r', isMatch ? nodeSize.TF.highlight : nodeSize.TF.base);
            } else if (d.moltype === 'ligand') {
                g.select('path').attr('d', d3.symbol().type(d3.symbolTriangle).size(isMatch ? nodeSize.ligand.highlight : nodeSize.ligand.base));
            } else if (d.moltype === 'receptor') {
                const side = isMatch ? nodeSize.receptor.highlight : nodeSize.receptor.base;
                g.select('rect').attr('width',side).attr('height', side).attr('x', -side/2).attr('y', -side/2);
            }
        });
	}

 	// TF nodes are merged if identical sets of:
	//   - outgoing links (same target id + weight)
	//   - incoming links (same source id + weight)
export function deduplicateTFs(rawNodes: any[], rawLinks: any[]): { nodes: any[]; links: any[] } {
		const tfNodes = rawNodes.filter((n) => n.moltype === 'TF');
		const nonTFNodes = rawNodes.filter((n) => n.moltype !== 'TF');

		// signature for each TF node
		const getId = (x: any) => (typeof x === 'object' && x !== null ? x.id : x);

        const sig = (n: any): string => {
            const out = rawLinks
                .filter((l) => getId(l.source) === n.id)
                .map((l) => `o:${getId(l.target)}:${l.weight}`)
                .sort()
                .join('|');
            const inc = rawLinks
                .filter((l) => getId(l.target) === n.id)
                .map((l) => `i:${getId(l.source)}:${l.weight}`)
                .sort()
                .join('|');
            return `${n.celltype}__${out}__${inc}`;  // also fixes the celltype bug
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

		const remappedLinks = rawLinks.map((l) => ({
            ...l,
            source: idMap.get(getId(l.source)) ?? getId(l.source),
            target: idMap.get(getId(l.target)) ?? getId(l.target),
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

export function applyCycleHighlight(
    cycleData: { nodeIds: Set<string>; edgePairs: Set<string> } | null,
    nodeSelection: any,
    linkSelection: any,
    //   colorScale: d3.ScaleOrdinal<string, string, string>,
    nodeSize = NODE_SIZES,
    fontSize = 9
    ) {
    if (!nodeSelection) return;

    if (!cycleData) {
        nodeSelection.attr('opacity', 1);
        linkSelection?.attr('opacity', 1);
        resetNodesSize(nodeSelection, nodeSize);
        nodeSelection.selectAll('.cycle-label').remove(); 
        nodeSelection.selectAll('.cycle-ring').remove();
        return;
    }

    const { nodeIds, edgePairs } = cycleData;

    const normalizedIds = new Set([...nodeIds].map(String));

    nodeSelection.attr('opacity', (d: any) => (normalizedIds.has(String(d.id)) ? 1 : 0.12));

    linkSelection?.attr('opacity', (l: any) => {
        const srcId = String(typeof l.source === 'object' ? l.source.id : l.source);
        const tgtId = String(typeof l.target === 'object' ? l.target.id : l.target);
        return edgePairs.has(`${srcId}->${tgtId}`) || edgePairs.has(`${tgtId}->${srcId}`) ? 1 : 0.06;
    });
    // aesEdge(linkSelection, 'volcano', 'endShape');

    nodeSelection.selectAll('.cycle-label').remove();
    nodeSelection.selectAll('.cycle-ring').remove();

    nodeSelection.each(function (this: SVGGElement, d: any) {
        const g = d3.select(this);
        const inCycle = normalizedIds.has(String(d.id));

        if (d.moltype === 'TF') {
        g.select('circle').attr('r', inCycle ? nodeSize.TF.highlight : nodeSize.TF.base);
        } else if (d.moltype === 'ligand') {
        g.select('path').attr(
            'd',
            d3.symbol().type(d3.symbolTriangle).size(inCycle ? nodeSize.ligand.highlight : nodeSize.ligand.base)
        );
        } else if (d.moltype === 'receptor') {
        const side = inCycle ? nodeSize.receptor.highlight : nodeSize.receptor.base;
        g.select('rect')
            .attr('width', side).attr('height', side)
            .attr('x', -side / 2).attr('y', -side / 2);
        }

        if (!inCycle) return;

        // const cellColor = colorScale(d.celltype);
        if (d.moltype === 'TF') {
        g.insert('circle', ':first-child')  // behind the fill circle
            .attr('class', 'cycle-ring')
            .attr('r', nodeSize.TF.highlight + 2.5)
            .attr('fill', 'none')
            // .attr('stroke', cellColor)
            .attr('stroke-width', 2);
        } else if (d.moltype === 'ligand') {
        g.insert('path', ':first-child')
            .attr('class', 'cycle-ring')
            .attr('d', d3.symbol().type(d3.symbolTriangle).size(nodeSize.ligand.highlight + 40))
            .attr('fill', 'none')
            // .attr('stroke', cellColor)
            .attr('stroke-width', 2);
        } else if (d.moltype === 'receptor') {
        const side = nodeSize.receptor.highlight + 5;
        g.insert('rect', ':first-child')
            .attr('class', 'cycle-ring')
            .attr('width', side).attr('height', side)
            .attr('x', -side / 2).attr('y', -side / 2)
            .attr('fill', 'none')
            // .attr('stroke', cellColor)
            .attr('stroke-width', 2);
        }

        const labelOffset = d.moltype === 'TF'
        ? nodeSize.TF.highlight + 5
        : d.moltype === 'receptor'
            ? nodeSize.receptor.highlight / 2 + 7
            : 13; // ligand triangle: roughly half height

        g.append('text')
        .attr('class', 'cycle-label')
        .attr('text-anchor', 'middle')
        .attr('dy', labelOffset)
        .attr('font-size', fontSize)
        .attr('font-weight', '600')
        .attr('stroke', 'var(--color-surface, #fff)')
        .attr('stroke-width', '1px')
        .attr('paint-order', 'stroke')   // stroke renders behind fill 
        .text(d.name);
    });
}