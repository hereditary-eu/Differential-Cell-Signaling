// define here the common variables and functions for network visualizations
import * as d3 from 'd3';

// export variables and function to define dimension of plot, zoom behavior and initial position with initial zoom level
export const width = 350;
export const height = 250;
const initialScale = 0.3;
const initialX = width / 3;
const initialY = height / 3;

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
export function drawShape(
    selection: d3.Selection<any, any, any, any>,
    colorScale: (value: string) => string
) {
		selection.each(function (d: any) {
			const g = d3.select(this);

			if (d.moltype === 'TF') {
				g.append('circle').attr('r', 7).attr('fill', colorScale(d.celltype));
			} else if (d.moltype === 'ligand') {
				const size = 80;
				g.append('path')
					.attr('d', d3.symbol().type(d3.symbolTriangle).size(size))
					.attr('fill', colorScale(d.celltype));
			} else if (d.moltype === 'receptor') {
				const side = 12;
				g.append('rect')
					.attr('x', -side / 2)
					.attr('y', -side / 2)
					.attr('width', side)
					.attr('height', side)
					.attr('fill', colorScale(d.celltype));
			}
		});
        // return selection;
        // without this, returns void! eventually add return selection for chaining
	}


// interpolateViridis wants values between 0 and 1 -> do minmax scale
// TODO in the future, now assuming scSeqComm output: [-1,1]
export function aesEdge(
    selection: d3.Selection<any, any, any, any>
) {

        selection.each(function (d: any) {
            const g = d3.select(this);
            g.attr('stroke', '#999'); // default color for other edges
            
            if (d.type === 'LR') {
                // VIRIDIS OPTION
                // const norm_weight = (d.weight + 1) / 2; // assuming [-1,1]
                // g.attr('stroke', d3.interpolateViridis(norm_weight));
                if (d.weight < 0) {
                    g.attr('stroke', '#1E90FF'); // blue for under-activation
                } else {
                    g.attr('stroke', '#720000'); //'#8B0000'); // darkred for over-activation
                }
                g.attr('stroke-opacity', 0.8);
                
            } else if (d.type === 'TFL') {
                if (d.weight < 0) {
                    // blunt end
                    g.attr('marker-end', 'url(#Tblunt)'); // not working
                    // g.attr('stroke', '#000000'); //DEBUG
                    // console.log('blunt end for TFL with weight <0')
                } else {
                    // arrow end
                    // g.attr('stroke', '#FFA500'); //DEBUG
                    g.attr('marker-end', 'url(#arrow)'); // not working
                    // console.log('arrow end for TFL with weight >=0')
                    
                }
            }
        });
}


// export function to be called when a node is clicked
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
    colorScale: d3.ScaleOrdinal<string, any, undefined>,
    symbolSize: number = 6,
    spacing: number = 7,
    fontSize: number = 5
) {
    // cell type legend
    const g = d3
        .select(svg)
        .append("g")
        .attr("class", "legend")
        .attr("transform", "translate(5, 10)");
        g.append("text")
            .attr("class", "legend-title")
            .attr("x", -1)
            .attr("y", -3) // adjust this for distance from legend
            .style("font-size", `${fontSize + 1}px`)
            .text('Cell types:');
    const items = colorScale.domain();
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
}
