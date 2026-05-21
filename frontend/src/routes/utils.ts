// define here the common variables and functions for network visualizations
import * as d3 from 'd3';

const NODE_SIZES = {
	TF: { base: 6, highlight: 10 },
	ligand: { base: 70, highlight: 180 },
	receptor: { base: 10, highlight: 16 }
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

export function updateNodeColors(
    nodeSelection: d3.Selection<any, any, any, any>, 
    colorScale: d3.ScaleOrdinal<string, string, string>, 
    aesSettings: any) {
		if (!nodeSelection) return;
		nodeSelection.each(function (this: any, d: any) {
			const g = d3.select(this as Element);
			const fill = aesSettings.CT ? colorScale(d.celltype) : '#a9a9a9';
			g.select('circle').attr('fill', fill);
            g.select('path').attr('fill', fill);
            g.select('rect').attr('fill', fill);
		});
	}
export function updateEdgesAes(linkSelection: d3.Selection<any, any, any, any>, aesSettings: any) {
		if (!linkSelection) return;
		linkSelection.call((sel: any) => aesEdge(sel, aesSettings.LR, aesSettings.TF));
	}
export function addNodesLabel(nodeSelection: d3.Selection<any, any, any, any>, fontSize: number = 9, nodeSize = NODE_SIZES) {
    if (!nodeSelection) return;
    nodeSelection
		.append('text')
            .attr('class', 'node-label')
            .attr('text-anchor', 'middle')
            .attr('font-size', fontSize)
            .attr('font-weight', '300')
            .attr('color', '#000000')
            .attr('fill', '#000000')
            .attr('stroke', '#000000')
            .attr('dy', (d: any) => {
                return d.moltype === 'TF'
                    ? nodeSize.TF.base + 10
                    : d.moltype === 'receptor'
                        ? nodeSize.receptor.base / 2 + 10
                        : 13; // triangle/ligand
            })
            .text((d: any) => d.name);

}
// export function to be called when a node is CLICKED (it's not related to sidebarSearch)
export function highlightNode(selectedId: string | null, links: any, node: d3.Selection<any, any, any, any>, link: d3.Selection<any, any, any, any>) {
    if (!selectedId) {
		node.attr('opacity', 1);
		link.attr('opacity', 1);
		return;
	}
    
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

    // add label to the selected node
    addNodesLabel(node.filter((d: any) => d.id === selectedId));
}

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

export function resetNodesSize (nodeSelection: any, nodeSize = NODE_SIZES) {
    nodeSelection.selectAll('circle').attr('r', nodeSize.TF.base);
    nodeSelection.selectAll('rect')
            .attr('width', nodeSize.receptor.base)
            .attr('height', nodeSize.receptor.base)
            .attr('x', -nodeSize.receptor.base/2)
            .attr('y', -nodeSize.receptor.base/2);
    nodeSelection.selectAll('path')
        .attr('d', d3.symbol().type(d3.symbolTriangle).size(nodeSize.ligand.base));
    // remove labels if any
    nodeSelection.selectAll('.node-label').remove();
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
        addNodesLabel(nodeSelection.filter((d: any) => matchIds.has(d.id)), 11, nodeSize);
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
		const idMap = new Map<number | string, number | string>();
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
    colorScale: d3.ScaleOrdinal<string, string, string>,
    aesSettings: any,
    nodeSize = NODE_SIZES,
    fontSize = 9
    ) {
    if (!nodeSelection) return;

    if (!cycleData) {
        nodeSelection.attr('opacity', 1);
        linkSelection?.attr('opacity', 1);
        resetNodesSize(nodeSelection, nodeSize);
        nodeSelection.selectAll('.node-label').remove(); 
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

    nodeSelection.selectAll('.node-label').remove();
    nodeSelection.selectAll('.cycle-ring').remove();

    updateNodeColors(nodeSelection, colorScale, aesSettings);
    updateEdgesAes(linkSelection, aesSettings);
    linkSelection?.attr('opacity', (l: any) => {
		const srcId = String(typeof l.source === 'object' ? l.source.id : l.source);
		const tgtId = String(typeof l.target === 'object' ? l.target.id : l.target);
		return edgePairs.has(`${srcId}->${tgtId}`) || edgePairs.has(`${tgtId}->${srcId}`) ? 1 : 0.06;
	});
    const cycleNodeSelection = nodeSelection.filter((d: any) =>
		normalizedIds.has(String(d.id))
	);
    addNodesLabel(cycleNodeSelection, fontSize, nodeSize);
}