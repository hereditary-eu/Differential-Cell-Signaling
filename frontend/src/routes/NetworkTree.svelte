<script lang="ts">
	import * as d3 from 'd3';
	import type { Node, Link, TreeNode, NeighborhoodData } from '$lib/types';
	// D3 variables...
	let svg: SVGSVGElement | null = null;
	let root: TreeNode | null = null;

	// props
	export let neighborhoodData: NeighborhoodData; // { rootnode, neighbors, links }
	export let width = 600;
	export let height = 600;

	// Build tree structure from nodes + links
	function buildTree(rootId: string | number, nodes: Node[], links: Link[]): TreeNode | null {
		const nodeMap = new Map(nodes.map((n) => [n.id, { ...n, children: [] } as TreeNode]));
		// Add all nodes to the map
		nodes.forEach((node) => {
			nodeMap.set(node.id, { ...node, children: [] });
		});
		nodeMap.set(neighborhoodData.rootnode.id, {
			...neighborhoodData.rootnode,
			children: []
		});

		links.forEach((l) => {
			const source = nodeMap.get(l.source);
			const target = nodeMap.get(l.target);
			if (source && target) {
				// Attach target as child of source if not already attached
				if (!source.children?.some((c) => c.id === target.id)) {
					source.children?.push(target);
				}
			}
		});
		return nodeMap.get(rootId) || null;
	}
	// update when neighborhoodData changes
	$: if (neighborhoodData) {
		console.log('Building tree with neighborhoodData:', neighborhoodData);
		root = buildTree(
			neighborhoodData.rootnode.id,
			neighborhoodData.neighbors,
			neighborhoodData.links
		);
		renderTree();
	}
	// Render when SVG is available and root is built
	$: if (svg && root) {
		console.log('Rendering tree with root:', root);
		renderTree();
	}
	function renderTree() {
		if (!root || !svg) return;
		// Clear previous content
		d3.select(svg).selectAll('*').remove();

		// Create tree layout with explicit typing
		const treeLayout = d3.tree<TreeNode>().size([height - 40, width - 100]);
		// Create hierarchy with explicit typing
		const hierarchy = d3.hierarchy<TreeNode>(root, (d: TreeNode) => d.children);
		const treeData = treeLayout(hierarchy);
		d3.select(svg).attr('width', width).attr('height', height);

		// still dont understand why we need this line
		const g = d3.select(svg).append('g').attr('transform', 'translate(50,20)');

		const linkGenerator = d3
			.linkHorizontal<d3.HierarchyPointLink<TreeNode>, d3.HierarchyPointNode<TreeNode>>()
			.x((d: d3.HierarchyPointNode<TreeNode>) => d.y)
			.y((d: d3.HierarchyPointNode<TreeNode>) => d.x);

		// Links
		g.selectAll('.link')
			.data(treeData.links())
			.enter()
			.append('path')
			.attr('class', 'link')
			.attr('d', linkGenerator)
			.attr('fill', 'none')
			.attr('stroke', '#555')
			.attr('stroke-width', 1.5);

		// Draw nodes
		const nodeGroups = g
			.selectAll('.node')
			.data(treeData.descendants())
			.enter()
			.append('g')
			.attr('class', 'node')
			.attr('transform', (d: d3.HierarchyPointNode<TreeNode>) => `translate(${d.y},${d.x})`);

		nodeGroups
			.append('text')
			.attr('dy', 3)
			.attr('x', (d) => (d.children ? -10 : 10))
			.style('text-anchor', (d) => (d.children ? 'end' : 'start'))
			.text((d) => `${d.data.name} (${d.data.moltype} ${d.data.celltype})`);
	}
</script>

<svg bind:this={svg}></svg>
