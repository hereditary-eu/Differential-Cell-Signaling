export interface Node {
		id: string | number;
		name: string;
		celltype: string;
		moltype?: string;
		[other: string]: any; // extra properties
	}
export interface Link {
		source: string | number;
		target: string | number;
		weight?: number;
		significance?: number;
		comparison?: string;
		[other: string]: any;
	}
export interface NeighborhoodData {
		rootId: number;
		nodes: Node[];
		links: Link[];
	}