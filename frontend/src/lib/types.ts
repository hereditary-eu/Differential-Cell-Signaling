export interface Node {
		id: string | number;
		name: string;
		celltype: string;
		moltype?: string;
		[other: string]: any; // catch-all for extra properties
	}
export interface Link {
		source: string | number;
		target: string | number;
		weight?: number;
		significance?: number;
		comparison?: string;
		[other: string]: any;
	}
export interface TreeNode extends Node {
		children?: TreeNode[];
		depth?: number; // optional distance from root
	}
export interface NeighborhoodData {
		rootnode: Node;
		neighbors: Node[];
		links: Link[];
	}