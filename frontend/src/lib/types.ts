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
export interface GoTerm {
	source: string;
	native: string;
	name: string;
	p_value: number;
	significant: boolean;
	description: string | null;
	term_size: number;
	query_size: number;
	intersection_size: number;
	precision: number;
	recall: number;
	intersections: string[];
	gene_ratio: number | null;
}
export interface GoResults {
	query_size: number;
	background_size: number | null;
	n_significant: number;
	universe_warning: string | null;
	results: GoTerm[];
}
