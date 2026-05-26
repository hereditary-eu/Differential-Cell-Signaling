// ---------------------------------------------------------------------------
// Barycenter heuristic to reduce edge crossings: sort nodes in each rank by the average position of their neighbors in the previous and next rank
// ---------------------------------------------------------------------------
	
export function barycentreSort(
    nodes: any[],
    rawLinks: any[],
    rankIndex: Map<string, number>,
    numRanks: number,
    max_iter = 6
): any[] {
    const adj = new Map<string, string[]>();
    for (const l of rawLinks) {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        if (!adj.has(s)) adj.set(s, []);
        if (!adj.has(t)) adj.set(t, []);
        adj.get(s)!.push(t);
        adj.get(t)!.push(s);
    }

    // Group nodes by rank
    const byRank: any[][] = Array.from({ length: numRanks }, () => []);
    const unranked: any[] = [];
    for (const n of nodes) {
        const ri = rankIndex.get(n.id);
        if (ri !== undefined && ri >= 0) byRank[ri].push(n);
        else unranked.push(n);
    }

    // Compute barycenter for one node given a position map of its neighbours.
    // Considers neighbours in BOTH the prev and next rank (weighted equally).
    // Returns Infinity only when the node has no ranked neighbours at all.
    const bary = (
        n: any,
        prevPos: Map<string, number> | null,
        nextPos: Map<string, number> | null
    ): number => {
        const nbrs = adj.get(n.id) ?? [];
        let sum = 0;
        let count = 0;
        for (const id of nbrs) {
            if (prevPos?.has(id)) { sum += prevPos.get(id)!; count++; }
            if (nextPos?.has(id)) { sum += nextPos.get(id)!; count++; }
        }
        return count > 0 ? sum / count : 1e9;
    };

    // Build a position map (by current order index) for a rank
    const posMap = (ri: number): Map<string, number> =>
        new Map(byRank[ri].map((n, i) => [n.id, i]));

    // Count crossings between rank ri and ri+1 (used to decide whether a
    // sweep improved the layout)
    const countCrossings = (ri: number): number => {
        if (ri < 0 || ri >= numRanks - 1) return 0;
        const posA = posMap(ri);
        const posB = posMap(ri + 1);
        let crossings = 0;
        const edges: [number, number][] = [];
        for (const l of rawLinks) {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            if (posA.has(s) && posB.has(t)) edges.push([posA.get(s)!, posB.get(t)!]);
            if (posA.has(t) && posB.has(s)) edges.push([posA.get(t)!, posB.get(s)!]);
        }
        for (let i = 0; i < edges.length; i++)
            for (let j = i + 1; j < edges.length; j++)
                if ((edges[i][0] - edges[j][0]) * (edges[i][1] - edges[j][1]) < 0) crossings++;
        return crossings;
    };

    const totalCrossings = (): number => {
        let t = 0;
        for (let ri = 0; ri < numRanks - 1; ri++) t += countCrossings(ri);
        return t;
    };

    // Snapshot current order for rollback
    const snapshot = (): any[][] => byRank.map(lane => [...lane]);
    const restore  = (snap: any[][]): void => { snap.forEach((lane, ri) => { byRank[ri] = lane; }); };

    // Single sweep in one direction
    const sweep = (forward: boolean) => {
        const range = forward
            ? Array.from({ length: numRanks }, (_, i) => i)
            : Array.from({ length: numRanks }, (_, i) => numRanks - 1 - i);

        for (const ri of range) {
            const lane = byRank[ri];
            if (lane.length <= 1) continue;
            const prev = ri > 0           ? posMap(ri - 1) : null;
            const next = ri < numRanks - 1 ? posMap(ri + 1) : null;
            lane.sort((a, b) => bary(a, prev, next) - bary(b, prev, next));
        }
    };

    let best = snapshot();
    let bestScore = totalCrossings();

    for (let iter = 0; iter < max_iter; iter++) {
        sweep(iter % 2 === 0); // alternate forward / backward
        const score = totalCrossings();
        if (score < bestScore) {
            bestScore = score;
            best = snapshot();
        } else if (score === bestScore) {
            break; // converged
        }
    }

    restore(best);
    return [...byRank.flat(), ...unranked];
}