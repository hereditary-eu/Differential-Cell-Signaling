// define here the common variables and functions for network visualizations
import * as d3 from 'd3';

export const width = 250;
export const height = 200;
const initialScale = 0.18;
const initialX = width / 2;
const initialY = height / 2.4;

const NODE_SIZES = {
	TF: { base: 7, highlight: 12 },
	ligand: { base: 80, highlight: 200 },
	receptor: { base: 12, highlight: 18 }
};

export interface ZoomOptions {
    scaleExtent?: [number, number];
    wheelSensitivity?: number;
    initialTransform?: d3.ZoomTransform;
}
export function zoomBehavior(
    zoomLayer: d3.Selection<SVGGElement, unknown, null, undefined>,
    options: ZoomOptions = {}
) {
    const {
        scaleExtent = [0.01, 10],
        wheelSensitivity = 0.002,
        initialTransform = d3.zoomIdentity.translate(initialX, initialY).scale(initialScale)
    } = options;

    const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent(scaleExtent)
        .wheelDelta((event) => -event.deltaY * wheelSensitivity)
        .on('zoom', (event) => {
            zoomLayer.attr('transform', event.transform);
        });

    return { zoom, initialTransform };
}

// export function to map moltype to shape
export function drawNode(
    selection: d3.Selection<any, any, any, any>,
    colorScale: d3.ScaleOrdinal<string, string, string>,
    color: boolean,
    nodeSize = NODE_SIZES
) {
		selection.each(function (d: any) {
			const g = d3.select(this);
			if (d.moltype === 'TF') {
				g.append('circle').attr('r', NODE_SIZES.TF.base).attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			} else if (d.moltype === 'ligand') {
				g.append('path')
					.attr('d', d3.symbol().type(d3.symbolTriangle).size(NODE_SIZES.ligand.base))
					.attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			} else if (d.moltype === 'receptor') {
				g.append('rect')
					.attr('x', -NODE_SIZES.receptor.base / 2)
					.attr('y', -NODE_SIZES.receptor.base / 2)
					.attr('width', NODE_SIZES.receptor.base)
					.attr('height', NODE_SIZES.receptor.base)
					.attr('fill', color ? colorScale(d.celltype): '#a9a9a9');
			}
		});
        // return selection;
        // without this, returns void! eventually add return selection for chaining
	}

// interpolateViridis wants values between 0 and 1 -> do minmax scale
// TODO in the future, now assuming scSeqComm output: [-1,1]
export function aesEdge(
    selection: d3.Selection<any, any, any, any>,
    aesLRMapping: 'reset' | 'viridis' | 'volcano',
    aesTFMapping: 'reset' | 'endShape'
) {
        selection.each(function (d: any) {
            const g = d3.select(this);
            g.attr('stroke', '#999'); // default color for other edges
            if (d.type === 'LR') {
                if (aesLRMapping === 'viridis') {
                    const norm_weight = (d.weight + 1) / 2; // assuming [-1,1]
                    g.attr('stroke', d3.interpolateViridis(norm_weight));
                } else if (aesLRMapping === 'volcano') {
                    if (d.weight < 0) {
                        g.attr('stroke', '#2166ac'); // blue for under-activation
                    } else {
                        g.attr('stroke', '#b2182b'); //'#8B0000'); // darkred for over-activation
                    }
                }
                g.attr('stroke-opacity', 1);
                
            } else if (d.type === 'TFL') {
                if (aesTFMapping === 'endShape') {
                    if (d.weight < 0) {
                        // blunt end
                        g.attr('marker-end', 'url(#Tblunt)');
                    } else {
                        // arrow end
                        g.attr('marker-end', 'url(#arrow)'); 
                    }
            }
        }
        });
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

// export function to draw legend of moltype and celltype
// to do: make same size triangle and square.. more similar to parameters used for plotting
export function drawLegend(
    svg: SVGSVGElement,
    colorScale: d3.ScaleOrdinal<string, any, string>,
    aesLRMapping: 'reset' | 'viridis' | 'volcano',
    aesTFMapping: 'reset' | 'endShape',
    sender: string,
    receiver: string,
    colorCT: boolean = true,
    symbolSize: number = 6,
    spacing: number = 7,
    fontSize: number = 4,
    full_net: boolean = false
) {
    const g = d3
        .select(svg)
        .append("g")
        .attr("class", "legend")
        .attr("transform", "translate(5, 10)");
    // cell type legend
    // if (colorCT) {
        g.append("text")
            .attr("class", "legend-title")
            .attr("x", -1)
            .attr("y", -3) // adjust this for distance from legend
            .style("font-size", `${fontSize + 1}px`)
            .text('Cell types:');
    const items = colorScale.domain().filter((i) => i === sender || i === receiver);
    const group = g
        .selectAll("g.legend-item")
        .data(items)
        .enter()
        .append("g")
        .attr("class", "legend-item")
        .attr("transform", (_, i) => `translate(0, ${i * spacing})`);
    group
        .append("rect")
        .attr("width", symbolSize)
        .attr("height", symbolSize)
        .attr("fill", d => colorScale(d));
    group
        .append("text")
        .attr("x", symbolSize + 4)
        .attr("y", symbolSize / 2)
        .attr("dominant-baseline", "middle")
        .style("font-size", `${fontSize}px`)
        .text(d => d);
    // } else {
    //     const items = [];
    // }
    //moltype legend
    const m = d3.select(svg).append("g").attr("class", "legend").attr("transform", `translate(5, ${20 + items.length * spacing + 2})`);
    m.append("text")
        .attr("class", "legend-title")
        .attr("x", -1)
        .attr("y", -5) // adjust this for distance from legend
        .style("font-size", `${fontSize + 1}px`)
        .text('Molecule:');
    const moltypes = ['TF', 'ligand', 'receptor'];
    const moltypeGroup = m
        .selectAll("g.moltype-legend-item")
        .data(moltypes)
        .enter()
        .append("g")
        .attr("class", "moltype-legend-item")
        .attr("transform", (_, i) => `translate(3, ${i * spacing})`);
    moltypeGroup
        .append("path")
        .attr("d", d3.symbol().type((d) => {
            if (d === 'TF') return d3.symbolCircle;
            else if (d === 'ligand') return d3.symbolTriangle;
            else if (d === 'receptor') return d3.symbolSquare;
            else return d3.symbolCircle;
        }).size(symbolSize*3))
        .attr("fill", "black");
    moltypeGroup
        .append("text")
        .attr("x", symbolSize + 0)
        .attr("y", symbolSize / 12)
        .attr("dominant-baseline", "middle")
        .style("font-size", `${fontSize}px`)
        .text(d => d);
    if (!full_net) {
        // LR legend
        // let offsetY = 50 + ( colorCT ? items.length * spacing : 0 );
        let offsetY = 50 + items.length * spacing ;
        if (aesLRMapping !== 'reset') {
            const lrLegend = d3.select(svg).append("g").attr("class", "legend").attr("transform", `translate(5, ${offsetY})`);
            lrLegend.append("text")
            .style("font-size", `${fontSize + 1}px`)
            .text("LR diff.:");
            const data = [
            { label: "Up", color: aesLRMapping === 'volcano' ? "#b2182b" : d3.interpolateViridis(1) },
            { label: "Down", color: aesLRMapping === 'volcano' ? "#2166ac" : d3.interpolateViridis(0) }
            ];
            const group = lrLegend
            .selectAll("g.lr-item")
            .data(data)
            .enter()
            .append("g")
            .attr("transform", (_, i) => `translate(0, ${(i + 1) * spacing})`);

            group.append("line")
                .attr("x1", 0)
                .attr("x2", symbolSize + 3)
                .attr("stroke-width", 2)
                .attr("stroke", d => d.color);

            group.append("text")
                .attr("x", symbolSize + 6)
                .attr("y", 0)
                .attr("dominant-baseline", "middle")
                .style("font-size", `${fontSize}px`)
                .text(d => d.label);

            offsetY += 25; // add space before tfl legend
        }
        // TFL legend
        if (aesTFMapping === 'endShape') {
            const tfLegend = d3.select(svg)
                .append("g")
                .attr("class", "legend")
                .attr("transform", `translate(5, ${offsetY})`);
            tfLegend.append("text")
                .style("font-size", `${fontSize + 1}px`)
                .text("TF regulation:");
            const data = [
                { label: "Promoting", marker: "url(#arrow)" },
                { label: "Inhibiting", marker: "url(#Tblunt)" }
            ];
            const group = tfLegend
                .selectAll("g.tf-item")
                .data(data)
                .enter()
                .append("g")
                .attr("transform", (_, i) => `translate(0, ${(i + 1) * spacing})`);

            group.append("line")
                .attr("x1", 0)
                .attr("x2", 10)
                .attr("y1", 0)
                .attr("y2", 0)
                .attr("stroke", "#999")
                .attr("stroke-width", 0.5)
                .attr("marker-end", d => d.marker)
                .attr("fill", "none");

            group.append("text")
                .attr("x", symbolSize + 6)
                .attr("y", 0)
                .attr("dominant-baseline", "middle")
                .style("font-size", `${fontSize}px`)
                .text(d => d.label);
                }
            }
}
export function trimPath(source: { x: number; y: number }, target: { x: number; y: number }, r = 12) {
			const dx = target.x - source.x;
			const dy = target.y - source.y;
			const dist = Math.sqrt(dx * dx + dy * dy);

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
    console.log('called resetNodesSize')    
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
			// Match all nodes sharing this molecule name
			const name = value.slice(5);
			matchIds = new Set(
				(networkData?.nodes ?? []).filter((n: any) => n.name === name).map((n: any) => n.id)
			);
		} else {
			// Match exact verbose_id (name__celltype) to single node
			matchIds = new Set(
				(networkData?.nodes ?? []).filter((n: any) => n.verbose_id === value).map((n: any) => n.id)
			);
		}
		nodeSelection.attr('opacity', (d: any) => (matchIds.has(d.id) ? 1 : 0.15));
		linkSelection?.attr('opacity', 0.15);

        // increase size
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
export	function deduplicateTFs(rawNodes: any[], rawLinks: any[]): { nodes: any[]; links: any[] } {
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
